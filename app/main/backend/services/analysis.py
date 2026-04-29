import logging
import re
from typing import Callable, Optional

from core.config import settings
from services.checks import run_rule_based_check
from services.diarization import DiarizationResult, Segment
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

from infra.storage.db.models import Call, Check, CheckResult, SpeakerTurn, User

logger = logging.getLogger(__name__)


def _normalize_phone_for_match(phone: str | None) -> str:
    """Strip everything except digits, drop leading 7/8 to compare equivalent forms."""
    if not phone:
        return ""
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    return digits


async def _build_speaker_map_stereo(
    diar_result: DiarizationResult, call: Call, db: AsyncSession,
) -> dict[str, str]:
    """
    Stereo telephony case. Convention: CHANNEL_0 == call.from_number side,
    CHANNEL_1 == call.to_number side. Resolve which side is the manager by
    looking up phone numbers in the users table.
    """
    labels = sorted(diar_result.speaker_labels)
    fallback = {labels[0]: "manager", labels[1]: "client"} if len(labels) >= 2 else {}

    from_norm = _normalize_phone_for_match(call.from_number)
    to_norm = _normalize_phone_for_match(call.to_number)

    if not from_norm and not to_norm:
        logger.info("Stereo: no from/to phones — falling back to channel-order labels")
        return fallback

    candidates = [p for p in (from_norm, to_norm) if p]
    res = await db.execute(select(User).where(User.phone_number.is_not(None)))
    user_phones = {
        _normalize_phone_for_match(u.phone_number) for u in res.scalars().all()
    }
    user_phones.discard("")

    manager_side: str | None = None  # "from" or "to"
    if from_norm and from_norm in user_phones:
        manager_side = "from"
    elif to_norm and to_norm in user_phones:
        manager_side = "to"

    if manager_side is None:
        logger.info(
            "Stereo: neither phone (%s, %s) found in users — fallback to channel order",
            call.from_number, call.to_number,
        )
        return fallback

    if manager_side == "from":
        mapping = {"CHANNEL_0": "manager", "CHANNEL_1": "client"}
    else:
        mapping = {"CHANNEL_0": "client", "CHANNEL_1": "manager"}
    logger.info(
        "Stereo: manager phone matched %s → mapping=%s", manager_side, mapping,
    )
    return mapping


async def _build_speaker_map_mono(
    diar_result: DiarizationResult,
) -> dict[str, str]:
    """
    Mono case. Pyannote split tracks already (we don't move text between
    speakers). LLM only LABELS which track is manager vs client.
    """
    if not diar_result.segments:
        return {}

    speaker_texts: dict[str, list[str]] = {}
    for seg in diar_result.segments:
        speaker_texts.setdefault(seg.speaker, []).append(seg.text)
    joined = {label: " ".join(parts) for label, parts in speaker_texts.items()}

    labels = sorted(joined.keys())
    if len(labels) == 1:
        return {labels[0]: "manager"}

    # Default fallback: first appearance = manager.
    fallback = {labels[0]: "manager"}
    for lbl in labels[1:]:
        fallback[lbl] = "client"

    manager_label = await identify_manager_speaker(joined)
    if manager_label is None or manager_label not in joined:
        logger.info("Mono: LLM didn't identify manager — fallback to first-speaker")
        return fallback

    mapping = {manager_label: "manager"}
    for lbl in labels:
        if lbl != manager_label:
            mapping[lbl] = "client"
    logger.info("Mono: LLM-identified manager=%s, mapping=%s", manager_label, mapping)
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

    diar_result = transcribe_with_diarization(audio_bytes)
    segments = diar_result.segments

    full_transcript = " ".join(seg.text for seg in segments)
    call.transcript = full_transcript
    call.status = "analyzing"
    await db.commit()
    _emit(on_progress, "analyzing", 40)

    # Build speaker → role mapping per the two policies:
    #  - Stereo + real telephony phones → phone lookup in users table
    #  - Mono OR manual upload (any channels) → LLM labels existing tracks
    #    without moving any chunks between speakers (that's pyannote's job)
    is_manual = (call.from_number or "").lower() == "manual"
    has_phones = bool(call.from_number) and not is_manual
    if diar_result.mode == "stereo" and has_phones:
        speaker_map = await _build_speaker_map_stereo(diar_result, call, db)
    else:
        speaker_map = await _build_speaker_map_mono(diar_result)
    logger.info(
        "Speaker mapping (mode=%s, manual=%s): %s",
        diar_result.mode, is_manual, speaker_map,
    )

    old_turns = await db.execute(
        select(SpeakerTurn).where(SpeakerTurn.call_id == call.id)
    )
    for old in old_turns.scalars().all():
        await db.delete(old)
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

    turns_text = "\n".join(
        f"[{t['speaker']}]: {t['text']}" for t in turns_dicts
    )

    metrics = compute_metrics(turns_dicts)
    if metrics.total_duration_sec > 0:
        call.duration_sec = int(metrics.total_duration_sec)

    checks_result = await db.execute(
        select(Check).where(Check.active == True)  # noqa: E712
    )
    active_checks = checks_result.scalars().all()

    # Очищаем ВСЕ прошлые результаты проверок звонка: если проверка была отключена после
    # предыдущего прогона, её stale-результат не должен оставаться в UI.
    await db.execute(delete(CheckResult).where(CheckResult.call_id == call.id))
    await db.flush()

    _emit(on_progress, "llm_checks", 60)

    for check in active_checks:
        if check.type == "rule_based" and check.rule_config:
            result_data = run_rule_based_check(
                rule_config=check.rule_config,
                transcript=call.transcript or "",
                turns=turns_dicts,
                output_type=check.output_type or "boolean",
            )

            check_result = CheckResult(
                call_id=call.id,
                check_id=check.id,
                **result_data,
            )
            db.add(check_result)

        elif check.type == "llm_based" and check.prompt:
            if settings.YANDEX_GPT_API_KEY and settings.YANDEX_GPT_FOLDER_ID:
                try:
                    result_data = await run_llm_check(
                        prompt_template=check.prompt,
                        transcript=call.transcript or "",
                        turns_text=turns_text,
                        output_type=check.output_type or "boolean",
                    )

                    check_result = CheckResult(
                        call_id=call.id,
                        check_id=check.id,
                        **result_data,
                    )
                    db.add(check_result)
                except LLMFatalError:
                    raise
                except Exception:
                    logger.exception(
                        "LLM check failed: check_id=%s, call_id=%s",
                        check.id,
                        call.id,
                    )

    _emit(on_progress, "summary", 90)

    if settings.YANDEX_GPT_API_KEY and settings.YANDEX_GPT_FOLDER_ID:
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
