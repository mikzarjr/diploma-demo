from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Callable, Optional

from src.metrics import extract_json
from src.models.llm_runners import RUNNERS, LLMResponse
from src.benchmark_llm_tasks import (
    SYSTEM_PROMPT, USER_TEMPLATE, CHECKLIST_KEYS, render_transcript,
)

CALLS_PATH = Path("data/labeled_calls/calls.json")
DEMO_OUT = Path("results/pipeline_demo.json")

OUTCOME_SCORE = {
    "deal_won": 100,
    "follow_up_scheduled": 70,
    "no_decision": 40,
    "unreachable": 20,
    "deal_lost": 10,
}


@dataclass
class TurnAnalysis:
    turn_id: int
    speaker: str
    text: str
    sentiment: Optional[str] = None


@dataclass
class CallAnalysis:
    call_id: str
    transcript: list[TurnAnalysis]
    checklist: dict
    checklist_score: float
    summary: str
    key_facts: list[str]
    sentiment_overall: str
    sentiment_timeline: list[dict]
    final_outcome: str
    quality_score: float
    grade: str
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


DiarizationFn = Callable[[str], list[dict]]


def transcribe_audio(wav_path: str) -> str:
    from src.models.t_one_runner import transcribe_t_one
    return transcribe_t_one(wav_path)


def assign_roles(turns: list[dict]) -> list[dict]:
    known = {"manager", "client"}
    if all(t.get("speaker") in known for t in turns):
        return turns
    first = turns[0].get("speaker") if turns else None
    out = []
    for t in turns:
        t = dict(t)
        t["speaker"] = "manager" if t.get("speaker") == first else "client"
        out.append(t)
    return out


def analyze_sentiment(turns: list[dict],
                      sentiment_fn: Optional[Callable[[str], str]] = None
                      ) -> tuple[list[TurnAnalysis], str, list[dict]]:
    if sentiment_fn is None:
        from src.models.sentiment_runners import transcribe_sentiment_xlm
        sentiment_fn = transcribe_sentiment_xlm

    analyzed: list[TurnAnalysis] = []
    client_labels: list[tuple[int, str]] = []
    for t in turns:
        ta = TurnAnalysis(turn_id=t.get("turn_id", len(analyzed)),
                          speaker=t["speaker"], text=t["text"])
        if t["speaker"] == "client" and t["text"].strip():
            ta.sentiment = sentiment_fn(t["text"])
            client_labels.append((ta.turn_id, ta.sentiment))
        analyzed.append(ta)

    if client_labels:
        counts: dict[str, int] = {}
        for _, lab in client_labels:
            counts[lab] = counts.get(lab, 0) + 1
        overall = max(counts, key=counts.get)
    else:
        overall = "neutral"

    timeline = []
    prev = None
    for tid, lab in client_labels:
        if lab != prev:
            timeline.append({"turn_id": tid, "label": lab})
            prev = lab
    return analyzed, overall, timeline


def analyze_llm(turns: list[dict], llm_model: str = "local_qwen_1_5b"
                ) -> tuple[dict, str, list[str], str, LLMResponse]:
    runner = RUNNERS[llm_model]
    prompt = USER_TEMPLATE.format(transcript=render_transcript(turns))
    resp = runner(prompt, SYSTEM_PROMPT)
    parsed = extract_json(resp.text) if resp.text else None

    checklist = {k: False for k in CHECKLIST_KEYS}
    summary, key_facts, outcome = "", [], "no_decision"
    if isinstance(parsed, dict):
        raw_cl = parsed.get("checklist", {}) or {}
        for k in CHECKLIST_KEYS:
            v = raw_cl.get(k, False)
            if isinstance(v, dict):
                v = v.get("label", False)
            checklist[k] = v is True
        summary = parsed.get("summary", "") or ""
        key_facts = parsed.get("key_facts", []) or []
        outcome = parsed.get("final_outcome", "no_decision") or "no_decision"
    return checklist, summary, key_facts, outcome, resp


def score_call(checklist: dict, outcome: str) -> tuple[float, float, str]:
    n = len(checklist) or 1
    checklist_score = 100.0 * sum(1 for v in checklist.values() if v) / n
    outcome_score = OUTCOME_SCORE.get(outcome, 40)
    quality = 0.8 * checklist_score + 0.2 * outcome_score
    grade = ("A" if quality >= 85 else "B" if quality >= 70
    else "C" if quality >= 50 else "D")
    return round(checklist_score, 1), round(quality, 1), grade


def analyze_transcript(turns: list[dict], call_id: str = "call",
                       llm_model: str = "local_qwen_1_5b",
                       sentiment_fn: Optional[Callable[[str], str]] = None
                       ) -> CallAnalysis:
    t0 = time.perf_counter()
    turns = assign_roles(turns)

    analyzed, sentiment_overall, timeline = analyze_sentiment(turns, sentiment_fn)
    t_sentiment = time.perf_counter()

    checklist, summary, key_facts, outcome, resp = analyze_llm(turns, llm_model)
    t_llm = time.perf_counter()

    checklist_score, quality, grade = score_call(checklist, outcome)

    return CallAnalysis(
        call_id=call_id,
        transcript=analyzed,
        checklist=checklist,
        checklist_score=checklist_score,
        summary=summary,
        key_facts=key_facts,
        sentiment_overall=sentiment_overall,
        sentiment_timeline=timeline,
        final_outcome=outcome,
        quality_score=quality,
        grade=grade,
        meta={
            "llm_model": llm_model,
            "llm_error": resp.error,
            "sentiment_sec": round(t_sentiment - t0, 2),
            "llm_sec": round(t_llm - t_sentiment, 2),
            "total_sec": round(t_llm - t0, 2),
        },
    )


def analyze_audio(wav_path: str, call_id: str = "call",
                  diarization_fn: Optional[DiarizationFn] = None,
                  llm_model: str = "local_qwen_1_5b") -> CallAnalysis:
    text = transcribe_audio(wav_path)
    if diarization_fn is not None:
        segments = diarization_fn(wav_path)
        turns = [{"turn_id": i, "speaker": s["speaker"], "text": s.get("text", "")}
                 for i, s in enumerate(segments)]
        analysis = analyze_transcript(turns, call_id=call_id, llm_model=llm_model)
        analysis.meta["diarization"] = "external"
    else:
        turns = [{"turn_id": 0, "speaker": "manager", "text": text}]
        analysis = analyze_transcript(turns, call_id=call_id, llm_model=llm_model)
        analysis.meta["diarization"] = "none (mono, pyannote не подключён)"
    analysis.meta["asr_model"] = "T-one"
    return analysis


def format_report(a: CallAnalysis) -> str:
    lines = [
        f"╔══ Анализ звонка {a.call_id} ══",
        f"║ Оценка качества: {a.quality_score}/100  (грейд {a.grade})",
        f"║ Чек-лист выполнен на {a.checklist_score}%",
        f"║ Исход: {a.final_outcome}",
        f"║ Тональность клиента: {a.sentiment_overall}",
        "╠══ Чек-лист ══",
    ]
    for k, v in a.checklist.items():
        lines.append(f"║  [{'✓' if v else '✗'}] {k}")
    lines.append("╠══ Summary ══")
    lines.append(f"║  {a.summary or '(пусто)'}")
    lines.append("╠══ Ключевые факты ══")
    for f in a.key_facts:
        lines.append(f"║  • {f}")
    if a.sentiment_timeline:
        lines.append("╠══ Динамика тональности ══")
        path = " → ".join(f"[{p['turn_id']}]{p['label']}" for p in a.sentiment_timeline)
        lines.append(f"║  {path}")
    lines.append(f"╚══ обработано за {a.meta.get('total_sec', '?')} с "
                 f"(sentiment {a.meta.get('sentiment_sec', '?')} с, "
                 f"LLM {a.meta.get('llm_sec', '?')} с)")
    return "\n".join(lines)


def main(n_calls: int = 3, llm_model: str = "local_qwen_1_5b") -> None:
    calls = json.loads(CALLS_PATH.read_text(encoding="utf-8"))["calls"]
    calls = calls[:n_calls]
    print(f"Pipeline demo: {len(calls)} звонк(ов), LLM={llm_model}\n")

    results = []
    for c in calls:
        analysis = analyze_transcript(
            c["transcript"], call_id=c["call_id"], llm_model=llm_model)
        results.append(analysis.to_dict())
        print(format_report(analysis))
        print()

    Path("results").mkdir(exist_ok=True)
    DEMO_OUT.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"→ {DEMO_OUT} ({len(results)} звонков)")


if __name__ == "__main__":
    import sys

    n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 3
    main(n)
