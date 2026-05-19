import logging
from typing import Callable, Optional

from core.config import settings
from services.checks import run_rule_based_check
from services.diarization import DiarizationResult
from services.llm import (
    LLMFatalError,
    generate_summary,
    identify_manager_speaker,
    run_llm_check,
)
from services.metrics import CallMetrics, compute_metrics
from services.transcription import transcribe_with_diarization
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from infra.storage.db.models import Call, Check, CheckResult, SpeakerTurn

logger = logging.getLogger(__name__)


async def _build_speaker_map(diar_result: DiarizationResult) -> dict[str, str]:
    if not diar_result.segments:
        return {}

    speaker_texts: dict[str, list[str]] = {}
    for seg in diar_result.segments:
        speaker_texts.setdefault(seg.speaker, []).append(seg.text)
    joined = {label: " ".join(parts) for label, parts in speaker_texts.items()}

    labels = sorted(joined.keys())
    if len(labels) == 1:
        return {labels[0]: "manager"}

    fallback = {labels[0]: "manager"}
    for lbl in labels[1:]:
        fallback[lbl] = "client"

    manager_label = await identify_manager_speaker(joined)
    if manager_label is None or manager_label not in joined:
        logger.info("LLM didn't identify manager — fallback to first-speaker")
        return fallback

    mapping = {manager_label: "manager"}
    for lbl in labels:
        if lbl != manager_label:
            mapping[lbl] = "client"
    logger.info("LLM-identified manager=%s, mapping=%s", manager_label, mapping)
    return mapping


ProgressCallback = Optional[Callable[[str, int], None]]


def _emit(cb: ProgressCallback, step: str, percent: int) -> None:
    if cb is None:
        return
    try:
        cb(step, percent)
    except Exception:
        logger.exception("progress callback failed (step=%s, percent=%s)", step, percent)


async def analyze_call(
        call: Call,
        audio_bytes: bytes,
        db: AsyncSession,
        on_progress: ProgressCallback = None,
) -> CallMetrics:
    _emit(on_progress, "transcribing", 10)
    call.status = "transcribing"
    await db.commit()

    is_manual = (call.from_number or "").lower() == "manual"
    diar_result = transcribe_with_diarization(audio_bytes, force_mono=is_manual)
    segments = diar_result.segments

    full_transcript = " ".join(seg.text for seg in segments)
    call.transcript = full_transcript
    logger.info(
        "Transcript (%d chars): %s",
        len(full_transcript), full_transcript[:500],
    )
    call.status = "analyzing"
    await db.commit()
    _emit(on_progress, "analyzing", 40)

    speaker_map = await _build_speaker_map(diar_result)
    logger.info(
        "Speaker mapping (mode=%s, manual=%s): %s",
        diar_result.mode, is_manual, speaker_map,
    )

    await db.execute(delete(SpeakerTurn).where(SpeakerTurn.call_id == call.id))
    await db.flush()

    for seg in segments:
        turn = SpeakerTurn(
            call_id=call.id,
            speaker=speaker_map.get(seg.speaker, seg.speaker),
            text=seg.text,
            t_start=seg.t_start,
            t_end=seg.t_end,
        )
        db.add(turn)
    await db.commit()

    turns_result = await db.execute(
        select(SpeakerTurn)
        .where(SpeakerTurn.call_id == call.id)
        .order_by(SpeakerTurn.t_start)
    )
    turns = turns_result.scalars().all()
    turns_dicts = [
        {"speaker": t.speaker, "text": t.text, "t_start": t.t_start, "t_end": t.t_end}
        for t in turns
    ]
    turns_text = "\n".join(f"[{t['speaker']}]: {t['text']}" for t in turns_dicts)

    metrics = compute_metrics(turns_dicts)
    if metrics.total_duration_sec > 0:
        call.duration_sec = int(metrics.total_duration_sec)

    checks_result = await db.execute(
        select(Check).where(Check.active == True)  # noqa: E712
    )
    active_checks = checks_result.scalars().all()

    await db.execute(delete(CheckResult).where(CheckResult.call_id == call.id))
    await db.flush()

    _emit(on_progress, "llm_checks", 60)

    transcript_empty = not (call.transcript or "").strip()
    if transcript_empty:
        logger.warning(
            "Empty transcript for call_id=%s — skipping LLM checks and summary",
            call.id,
        )

    for check in active_checks:
        if check.type == "rule_based" and check.rule_config:
            result_data = run_rule_based_check(
                rule_config=check.rule_config,
                transcript=call.transcript or "",
                turns=turns_dicts,
                output_type=check.output_type or "boolean",
            )
            db.add(CheckResult(call_id=call.id, check_id=check.id, **result_data))

        elif check.type == "llm_based" and check.prompt:
            if transcript_empty:
                continue
            if not (settings.YANDEX_GPT_API_KEY and settings.YANDEX_GPT_FOLDER_ID):
                continue
            try:
                result_data = await run_llm_check(
                    prompt_template=check.prompt,
                    transcript=call.transcript or "",
                    turns=turns_dicts,
                    output_type=check.output_type or "boolean",
                )
                db.add(CheckResult(call_id=call.id, check_id=check.id, **result_data))
            except LLMFatalError:
                raise
            except Exception:
                logger.exception(
                    "LLM check failed: check_id=%s, call_id=%s", check.id, call.id,
                )

    _emit(on_progress, "summary", 90)

    if transcript_empty:
        call.summary = "Транскрипция недоступна — ASR не распознал речь."
    elif settings.YANDEX_GPT_API_KEY and settings.YANDEX_GPT_FOLDER_ID:
        try:
            call.summary = await generate_summary(call.transcript or "", turns_text)
        except LLMFatalError:
            raise
        except Exception:
            logger.exception("LLM summary failed: call_id=%s", call.id)

    call.status = "analyzed"
    await db.commit()
    _emit(on_progress, "done", 100)

    return metrics
