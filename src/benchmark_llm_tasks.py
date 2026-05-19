from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from src.models.llm_runners import RUNNERS, LLMResponse

CALLS_PATH = Path("data/labeled_calls/calls.json")
OUT_SUMMARY = Path("results/llm_task_eval.csv")
OUT_PREDICTIONS = Path("results/llm_task_predictions.csv")

CHECKLIST_KEYS = [
    "greeting", "self_introduction", "needs_discovery", "presentation",
    "objection_handling", "closing", "next_step_set",
]
OUTCOME_LABELS = ["deal_won", "deal_lost", "follow_up_scheduled", "no_decision", "unreachable"]

PRICING_RUB_PER_MTOK = {
    "yandex_lite": {"input": 200, "output": 200},
    "yandex_pro": {"input": 1200, "output": 1200},
    "local_qwen_1_5b": {"input": 0, "output": 0},
    "mock": {"input": 0, "output": 0},
}

SYSTEM_PROMPT = """Ты — аналитик отдела контроля качества B2B-звонков.
Тебе дают транскрипт диалога менеджер–клиент. Нужно вернуть СТРОГО валидный JSON
без какого-либо текста до или после JSON. Не пиши ```json или ``` — только сам объект."""

USER_TEMPLATE = """Проанализируй транскрипт звонка ниже.

Верни JSON со следующими полями:
- "checklist": объект с 7 пунктами, для каждого пункта значение true/false:
  - "greeting"           — поприветствовал ли менеджер клиента
  - "self_introduction"  — представился ли менеджер (имя или компания)
  - "needs_discovery"    — задал ли менеджер хотя бы 2 открытых вопроса о ситуации/задачах клиента
  - "presentation"       — описал ли менеджер своё предложение
  - "objection_handling" — обработал ли менеджер возражения клиента (если они были)
  - "closing"            — предложил ли менеджер конкретное действие в конце
  - "next_step_set"      — зафиксирована ли конкретная договорённость (дата/канал/etc.)
- "summary": строка 2–4 предложения, кто-зачем-что-возражения-итог
- "key_facts": массив строк, 3–10 коротких атомарных фактов из звонка
- "sentiment_overall": одна из строк "positive", "neutral", "negative" — тональность клиента в целом
- "final_outcome": одна из строк "deal_won", "deal_lost", "follow_up_scheduled", "no_decision", "unreachable"

Транскрипт:
{transcript}

JSON:"""


def render_transcript(turns: list[dict]) -> str:
    role = {"manager": "Менеджер", "client": "Клиент"}
    return "\n".join(f"[{t['turn_id']}] {role.get(t['speaker'], t['speaker'])}: {t['text']}"
                     for t in turns)


from src.metrics import (
    extract_json, cohen_kappa, per_class_f1, macro_f1_binary,
    rouge_l, fact_metrics,
)


@dataclass
class CallPrediction:
    call_id: str
    model: str
    parsed_ok: bool
    latency_sec: float
    input_tokens: int
    output_tokens: int
    raw_response: str
    error: Optional[str] = None
    checklist_pred: dict = field(default_factory=dict)
    summary_pred: str = ""
    facts_pred: list = field(default_factory=list)
    sentiment_pred: str = ""
    outcome_pred: str = ""


def run_model_on_calls(model_name: str, runner: Callable, calls: list[dict]) -> list[CallPrediction]:
    preds = []
    for call in calls:
        transcript = render_transcript(call["transcript"])
        user_prompt = USER_TEMPLATE.format(transcript=transcript)
        resp: LLMResponse = runner(user_prompt, SYSTEM_PROMPT)
        parsed = extract_json(resp.text) if resp.text else None
        ok = isinstance(parsed, dict)
        p = CallPrediction(
            call_id=call["call_id"],
            model=model_name,
            parsed_ok=ok,
            latency_sec=resp.latency_sec,
            input_tokens=resp.input_tokens_est,
            output_tokens=resp.output_tokens_est,
            raw_response=resp.text[:2000],
            error=resp.error,
        )
        if ok:
            p.checklist_pred = parsed.get("checklist", {}) or {}
            p.summary_pred = parsed.get("summary", "") or ""
            p.facts_pred = parsed.get("key_facts", []) or []
            p.sentiment_pred = parsed.get("sentiment_overall", "") or ""
            p.outcome_pred = parsed.get("final_outcome", "") or ""
        preds.append(p)
    return preds


def aggregate_metrics(preds: list[CallPrediction], calls_by_id: dict) -> dict:
    cl_true_all, cl_pred_all = [], []
    per_item_true: dict[str, list[int]] = {k: [] for k in CHECKLIST_KEYS}
    per_item_pred: dict[str, list[int]] = {k: [] for k in CHECKLIST_KEYS}

    rouges, fact_metrics_list = [], []
    sentiment_correct, outcome_correct = 0, 0
    parsed_ok_count = 0
    total_input_tokens, total_output_tokens, total_latency = 0, 0, 0.0

    n_evaluable = 0

    for p in preds:
        total_input_tokens += p.input_tokens
        total_output_tokens += p.output_tokens
        total_latency += p.latency_sec
        if not p.parsed_ok:
            continue
        parsed_ok_count += 1
        n_evaluable += 1
        gold = calls_by_id[p.call_id]["gold_labels"]
        for k in CHECKLIST_KEYS:
            gt = 1 if gold["checklist"].get(k, {}).get("label") else 0
            pr_raw = p.checklist_pred.get(k, False)
            if isinstance(pr_raw, dict):
                pr_raw = pr_raw.get("label", False)
            pr = 1 if pr_raw is True else 0
            cl_true_all.append(gt)
            cl_pred_all.append(pr)
            per_item_true[k].append(gt)
            per_item_pred[k].append(pr)
        rouges.append(rouge_l(gold["summary_reference"], p.summary_pred))
        fact_metrics_list.append(fact_metrics(gold["key_facts"], p.facts_pred))
        if p.sentiment_pred == gold["client_sentiment_overall"]:
            sentiment_correct += 1
        if p.outcome_pred == gold["final_outcome"]:
            outcome_correct += 1

    n_total = len(preds)
    avg = lambda xs: sum(xs) / len(xs) if xs else 0.0

    per_item_f1 = {k: per_class_f1(per_item_true[k], per_item_pred[k])["f1"] for k in CHECKLIST_KEYS}

    return {
        "n_calls": n_total,
        "n_parsed_ok": parsed_ok_count,
        "parse_rate": parsed_ok_count / n_total if n_total else 0.0,
        "checklist_accuracy": (sum(1 for t, p in zip(cl_true_all, cl_pred_all) if t == p) /
                               len(cl_true_all)) if cl_true_all else 0.0,
        "checklist_macro_f1": macro_f1_binary(cl_true_all, cl_pred_all) if cl_true_all else 0.0,
        "checklist_cohen_kappa": cohen_kappa(cl_true_all, cl_pred_all),
        "checklist_per_item_f1": per_item_f1,
        "summary_rouge_l": avg(rouges),
        "fact_precision": avg([m["fact_precision"] for m in fact_metrics_list]),
        "fact_recall": avg([m["fact_recall"] for m in fact_metrics_list]),
        "fact_f1": avg([m["fact_f1"] for m in fact_metrics_list]),
        "sentiment_accuracy": sentiment_correct / n_evaluable if n_evaluable else 0.0,
        "outcome_accuracy": outcome_correct / n_evaluable if n_evaluable else 0.0,
        "avg_latency_sec": total_latency / n_total if n_total else 0.0,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
    }


def estimate_cost_per_1000(model_name: str, agg: dict) -> Optional[float]:
    p = PRICING_RUB_PER_MTOK.get(model_name)
    if not p or agg["n_calls"] == 0:
        return None
    in_per_call = agg["total_input_tokens"] / agg["n_calls"]
    out_per_call = agg["total_output_tokens"] / agg["n_calls"]
    cost_per_call = (in_per_call * p["input"] + out_per_call * p["output"]) / 1_000_000
    return cost_per_call * 1000


def main(models: list[str] | None = None) -> None:
    calls = json.loads(CALLS_PATH.read_text(encoding="utf-8"))["calls"]
    calls_by_id = {c["call_id"]: c for c in calls}
    models = models or list(RUNNERS.keys())
    print(f"Calls: {len(calls)}, models: {models}")

    Path("results").mkdir(exist_ok=True)

    summary_rows = []
    pred_rows = []
    for model_name in models:
        if model_name not in RUNNERS:
            print(f"  ! Unknown model: {model_name}")
            continue
        print(f"\n=== {model_name} ===")
        preds = run_model_on_calls(model_name, RUNNERS[model_name], calls)
        agg = aggregate_metrics(preds, calls_by_id)
        agg["model"] = model_name
        agg["est_cost_rub_per_1000_calls"] = estimate_cost_per_1000(model_name, agg)
        for k, v in agg.pop("checklist_per_item_f1").items():
            agg[f"f1_{k}"] = v
        summary_rows.append(agg)
        for p in preds:
            pred_rows.append({
                "model": model_name,
                "call_id": p.call_id,
                "parsed_ok": p.parsed_ok,
                "latency_sec": round(p.latency_sec, 3),
                "input_tokens": p.input_tokens,
                "output_tokens": p.output_tokens,
                "error": p.error or "",
                "raw_response_head": p.raw_response[:300].replace("\n", " "),
            })
        print(f"  parse_rate={agg['parse_rate']:.2f}  "
              f"checklist_acc={agg['checklist_accuracy']:.3f}  "
              f"κ={agg['checklist_cohen_kappa']:.3f}  "
              f"rouge_l={agg['summary_rouge_l']:.3f}  "
              f"fact_f1={agg['fact_f1']:.3f}  "
              f"out_acc={agg['outcome_accuracy']:.3f}  "
              f"latency={agg['avg_latency_sec']:.2f}s")

    if summary_rows:
        keys = sorted({k for r in summary_rows for k in r.keys()})
        with OUT_SUMMARY.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            for r in summary_rows:
                w.writerow(r)
        print(f"\n→ {OUT_SUMMARY}")

    if pred_rows:
        with OUT_PREDICTIONS.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(pred_rows[0].keys()))
            w.writeheader()
            for r in pred_rows:
                w.writerow(r)
        print(f"→ {OUT_PREDICTIONS}")


if __name__ == "__main__":
    import sys

    models = sys.argv[1:] if len(sys.argv) > 1 else None
    main(models)
