from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Callable

from src.models.llm_runners import RUNNERS, LLMResponse
from src.benchmark_llm_tasks import PRICING_RUB_PER_MTOK
from src.metrics import rouge_l, rouge_n, normalize_for_fact, extract_json

OUT_SUMMARY = Path("results/dialogsum_eval.csv")
OUT_PREDICTIONS = Path("results/dialogsum_predictions.csv")

SYSTEM_PROMPT = """Ты — помощник, который кратко резюмирует деловые диалоги на русском.
Отвечай СТРОГО валидным JSON без какого-либо текста до или после."""

USER_TEMPLATE = """Дан диалог двух участников. Верни JSON:
- "summary": 1–3 предложения, передающие суть разговора, ключевых действующих лиц и итог;
- "topic": тема разговора одной строкой (1–5 слов).

Диалог:
{dialogue}

JSON:"""


def topic_match(gold: str, hyp: str, threshold: float = 0.5) -> bool:
    g, h = normalize_for_fact(gold), normalize_for_fact(hyp)
    if not g or not h:
        return False
    union = len(g | h)
    return union > 0 and (len(g & h) / union) >= threshold


def load_corpus(n: int, seed: int = 42, split: str = "test"):
    from datasets import load_dataset
    ds = load_dataset("d0rj/dialogsum-ru", split=split)
    if n < len(ds):
        import random
        rng = random.Random(seed)
        idxs = rng.sample(range(len(ds)), n)
        return [ds[i] for i in sorted(idxs)]
    return list(ds)


def run_on_corpus(model_name: str, runner: Callable, dialogues: list[dict]) -> tuple[list[dict], dict]:
    rouges_1, rouges_2, rouges_l = [], [], []
    topic_hits = 0
    parsed_ok = 0
    total_latency = 0.0
    total_in_tok = 0
    total_out_tok = 0
    rows = []

    for ex in dialogues:
        dialogue = ex["dialogue"]
        gold_summary = ex["summary"]
        gold_topic = ex.get("topic", "")
        resp: LLMResponse = runner(USER_TEMPLATE.format(dialogue=dialogue), SYSTEM_PROMPT)
        total_latency += resp.latency_sec
        total_in_tok += resp.input_tokens_est
        total_out_tok += resp.output_tokens_est
        parsed = extract_json(resp.text) if resp.text else None
        hyp_summary = ""
        hyp_topic = ""
        if isinstance(parsed, dict):
            parsed_ok += 1
            hyp_summary = parsed.get("summary", "") or ""
            hyp_topic = parsed.get("topic", "") or ""
        r1 = rouge_n(gold_summary, hyp_summary, 1)
        r2 = rouge_n(gold_summary, hyp_summary, 2)
        rl = rouge_l(gold_summary, hyp_summary)
        rouges_1.append(r1)
        rouges_2.append(r2)
        rouges_l.append(rl)
        t_match = topic_match(gold_topic, hyp_topic)
        topic_hits += int(t_match)
        rows.append({
            "model": model_name,
            "id": ex.get("id", ""),
            "gold_topic": gold_topic,
            "hyp_topic": hyp_topic,
            "topic_match": t_match,
            "rouge_1": round(r1, 4),
            "rouge_2": round(r2, 4),
            "rouge_l": round(rl, 4),
            "gold_summary_len": len(gold_summary),
            "hyp_summary_len": len(hyp_summary),
            "latency_sec": round(resp.latency_sec, 3),
            "error": resp.error or "",
        })

    n = len(dialogues)
    avg = lambda xs: sum(xs) / len(xs) if xs else 0.0
    agg = {
        "model": model_name,
        "n": n,
        "parse_rate": parsed_ok / n if n else 0.0,
        "rouge_1": round(avg(rouges_1), 4),
        "rouge_2": round(avg(rouges_2), 4),
        "rouge_l": round(avg(rouges_l), 4),
        "topic_accuracy": round(topic_hits / n, 4) if n else 0.0,
        "avg_latency_sec": round(total_latency / n, 3) if n else 0.0,
        "total_input_tokens": total_in_tok,
        "total_output_tokens": total_out_tok,
    }
    p = PRICING_RUB_PER_MTOK.get(model_name)
    if p and n:
        avg_in = total_in_tok / n
        avg_out = total_out_tok / n
        agg["est_cost_rub_per_1000"] = round((avg_in * p["input"] + avg_out * p["output"]) / 1000, 2)
    else:
        agg["est_cost_rub_per_1000"] = None
    return rows, agg


def main(models: list[str] | None = None, n: int = 100, split: str = "test", seed: int = 42):
    models = models or ["local_qwen_1_5b"]
    print(f"Loading {n} samples from d0rj/dialogsum-ru split={split} seed={seed} ...")
    dialogues = load_corpus(n, seed=seed, split=split)
    print(f"Loaded: {len(dialogues)} dialogues")

    Path("results").mkdir(exist_ok=True)
    all_rows, all_aggs = [], []
    for m in models:
        if m not in RUNNERS:
            print(f"  ! unknown model: {m}")
            continue
        print(f"\n=== {m} ===")
        rows, agg = run_on_corpus(m, RUNNERS[m], dialogues)
        all_rows.extend(rows)
        all_aggs.append(agg)
        print(f"  parse_rate={agg['parse_rate']:.2f}  "
              f"R1={agg['rouge_1']:.3f}  R2={agg['rouge_2']:.3f}  RL={agg['rouge_l']:.3f}  "
              f"topic_acc={agg['topic_accuracy']:.3f}  "
              f"latency={agg['avg_latency_sec']:.2f}s")

    if all_aggs:
        keys = list(all_aggs[0].keys())
        with OUT_SUMMARY.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            for r in all_aggs:
                w.writerow(r)
        print(f"\n→ {OUT_SUMMARY}")
    if all_rows:
        with OUT_PREDICTIONS.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
            w.writeheader()
            for r in all_rows:
                w.writerow(r)
        print(f"→ {OUT_PREDICTIONS}")


if __name__ == "__main__":
    args = sys.argv[1:]
    models = [a for a in args if not a.isdigit()]
    n = next((int(a) for a in args if a.isdigit()), 100)
    main(models or None, n=n)
