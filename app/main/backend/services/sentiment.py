import logging
from pathlib import Path
from typing import Iterable

from core.config import settings

logger = logging.getLogger(__name__)

SENTIMENT_DIR = Path(settings.SENTIMENT_MODEL_DIR).resolve()

_sent_pipe = None

_LABEL_MAP = {
    "label_0": "negative",
    "label_1": "neutral",
    "label_2": "positive",
    "negative": "negative",
    "neutral": "neutral",
    "positive": "positive",
}


def _norm_label(raw: str) -> str:
    return _LABEL_MAP.get((raw or "").strip().lower(), (raw or "neutral").lower())


def _get_pipe():
    global _sent_pipe
    if _sent_pipe is None:
        from transformers import pipeline as hf_pipeline

        logger.info("Loading sentiment pipeline from %s", SENTIMENT_DIR)
        _sent_pipe = hf_pipeline(
            "sentiment-analysis",
            model=str(SENTIMENT_DIR),
            tokenizer=str(SENTIMENT_DIR),
            top_k=None,
        )
        logger.info("Sentiment pipeline ready")
    return _sent_pipe


def _classify_one(text: str) -> dict:
    text = (text or "").strip()
    if not text:
        return {"label": "neutral", "score": 0.0}
    pipe = _get_pipe()
    try:
        raw = pipe(text[:512])
    except Exception:
        logger.exception("Sentiment failed on text len=%d", len(text))
        return {"label": "neutral", "score": 0.0}
    items = raw[0] if isinstance(raw, list) and raw and isinstance(raw[0], list) else raw
    if not items:
        return {"label": "neutral", "score": 0.0}
    if isinstance(items, dict):
        items = [items]
    best = max(items, key=lambda x: float(x.get("score", 0)))
    return {"label": _norm_label(best.get("label", "")), "score": float(best.get("score", 0.0))}


def analyze_turns(turns: Iterable[dict]) -> dict:
    turns_list = [t for t in turns if (t.get("text") or "").strip()]
    if not turns_list:
        return {"overall": {"label": "neutral", "score": 0.0}, "per_speaker": {}, "per_turn": []}

    per_turn: list[dict] = []
    by_speaker: dict[str, list[dict]] = {}
    for t in turns_list:
        text = (t.get("text") or "").strip()
        speaker = t.get("speaker") or "unknown"
        result = _classify_one(text)
        per_turn.append({
            "speaker": speaker,
            "text": text[:200],
            "label": result["label"],
            "score": result["score"],
        })
        by_speaker.setdefault(speaker, []).append(result)

    per_speaker: dict[str, dict] = {}
    for sp, items in by_speaker.items():
        dist = {"negative": 0, "neutral": 0, "positive": 0}
        total_score = 0.0
        for x in items:
            lbl = x["label"]
            if lbl in dist:
                dist[lbl] += 1
            total_score += x["score"]
        dominant = max(dist, key=dist.get)
        per_speaker[sp] = {
            "label": dominant,
            "avg_score": total_score / max(1, len(items)),
            "distribution": dist,
        }

    full_text = " ".join((t.get("text") or "") for t in turns_list)
    overall = _classify_one(full_text[:2000])

    return {"overall": overall, "per_speaker": per_speaker, "per_turn": per_turn}


def format_for_prompt(sent: dict, max_turns: int = 12) -> str:
    if not sent:
        return ""
    lines: list[str] = []
    overall = sent.get("overall") or {}
    lines.append(
        f"Общая тональность: {overall.get('label', 'neutral')} "
        f"(уверенность {overall.get('score', 0):.2f})"
    )
    per_speaker = sent.get("per_speaker") or {}
    for sp, info in per_speaker.items():
        dist = info.get("distribution", {})
        lines.append(
            f"- {sp}: преобладает {info.get('label')} "
            f"(avg={info.get('avg_score', 0):.2f}, "
            f"neg={dist.get('negative', 0)}/neu={dist.get('neutral', 0)}/pos={dist.get('positive', 0)})"
        )
    sample = (sent.get("per_turn") or [])[:max_turns]
    if sample:
        lines.append("Сэмпл реплик:")
        for t in sample:
            lines.append(
                f"  [{t.get('speaker')}] {t.get('label')} ({t.get('score', 0):.2f}): "
                f"{t.get('text', '')[:120]}"
            )
    return "\n".join(lines)
