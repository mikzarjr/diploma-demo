from __future__ import annotations

import csv
import json
import random
import sys
from copy import deepcopy
from pathlib import Path

from jiwer import wer as jiwer_wer

from src.models.llm_runners import RUNNERS
from src.benchmark_llm_tasks import (
    CALLS_PATH, CHECKLIST_KEYS, aggregate_metrics, run_model_on_calls,
)

OUT = Path("results/ablation_asr_propagation.csv")
OUT_ITEMS = Path("results/ablation_asr_baseline_items.csv")

WER_LEVELS = [0.0, 0.10, 0.20, 0.30, 0.40]


def build_vocab(calls: list[dict]) -> list[str]:
    vocab = set()
    for c in calls:
        for t in c["transcript"]:
            for w in t["text"].split():
                w = w.strip(".,!?:;«»\"()").lower()
                if len(w) > 1:
                    vocab.add(w)
    return sorted(vocab)


def degrade_text(text: str, target_wer: float, rng: random.Random,
                 vocab: list[str]) -> str:
    if target_wer <= 0:
        return text
    words = text.split()
    out = []
    for w in words:
        if rng.random() < target_wer:
            op = rng.choice(["sub", "del", "ins"])
            if op == "sub":
                out.append(rng.choice(vocab))
            elif op == "del":
                continue
            else:
                out.append(w)
                out.append(rng.choice(vocab))
        else:
            out.append(w)
    return " ".join(out) if out else text


def degrade_call(call: dict, target_wer: float, rng: random.Random,
                 vocab: list[str]) -> tuple[dict, float]:
    dc = deepcopy(call)
    clean_parts, dirty_parts = [], []
    for turn in dc["transcript"]:
        clean = turn["text"]
        dirty = degrade_text(clean, target_wer, rng, vocab)
        clean_parts.append(clean)
        dirty_parts.append(dirty)
        turn["text"] = dirty
    clean_full = " ".join(clean_parts)
    dirty_full = " ".join(dirty_parts)
    actual = jiwer_wer(clean_full, dirty_full) if clean_full.strip() else 0.0
    return dc, actual


def baseline_item_details(preds, calls_by_id) -> list[dict]:
    rows = []
    for p in preds:
        if not p.parsed_ok:
            continue
        gold = calls_by_id[p.call_id]["gold_labels"]
        for k in CHECKLIST_KEYS:
            gt = bool(gold["checklist"].get(k, {}).get("label"))
            pr_raw = p.checklist_pred.get(k, False)
            if isinstance(pr_raw, dict):
                pr_raw = pr_raw.get("label", False)
            pr = pr_raw is True
            rows.append({
                "call_id": p.call_id, "item": k,
                "gold": int(gt), "pred": int(pr),
                "correct": int(gt == pr),
            })
    return rows


def main(model_name: str = "local_qwen_1_5b", n_seeds: int = 2) -> None:
    calls = json.loads(CALLS_PATH.read_text(encoding="utf-8"))["calls"]
    calls_by_id = {c["call_id"]: c for c in calls}
    vocab = build_vocab(calls)
    runner = RUNNERS[model_name]
    print(f"Calls: {len(calls)}, vocab: {len(vocab)}, model: {model_name}, "
          f"levels: {WER_LEVELS}, seeds/level: {n_seeds}")

    Path("results").mkdir(exist_ok=True)
    rows = []

    for level in WER_LEVELS:
        seeds = [0] if level == 0.0 else list(range(n_seeds))
        for seed in seeds:
            rng = random.Random(1000 + int(level * 100) + seed)
            degraded, actual_wers = [], []
            for c in calls:
                dc, awer = degrade_call(c, level, rng, vocab)
                degraded.append(dc)
                actual_wers.append(awer)
            mean_actual_wer = sum(actual_wers) / len(actual_wers)

            preds = run_model_on_calls(model_name, runner, degraded)
            agg = aggregate_metrics(preds, calls_by_id)

            row = {
                "target_wer": level,
                "actual_wer": round(mean_actual_wer, 4),
                "seed": seed,
                "checklist_accuracy": round(agg["checklist_accuracy"], 4),
                "checklist_macro_f1": round(agg["checklist_macro_f1"], 4),
                "checklist_cohen_kappa": round(agg["checklist_cohen_kappa"], 4),
                "summary_rouge_l": round(agg["summary_rouge_l"], 4),
                "fact_f1": round(agg["fact_f1"], 4),
                "outcome_accuracy": round(agg["outcome_accuracy"], 4),
                "sentiment_accuracy": round(agg["sentiment_accuracy"], 4),
                "parse_rate": round(agg["parse_rate"], 4),
            }
            rows.append(row)
            print(f"  WER target={level:.2f} actual={mean_actual_wer:.3f} "
                  f"seed={seed}: checklist_acc={row['checklist_accuracy']:.3f} "
                  f"fact_f1={row['fact_f1']:.3f} outcome={row['outcome_accuracy']:.3f}")

            if level == 0.0:
                items = baseline_item_details(preds, calls_by_id)
                with OUT_ITEMS.open("w", encoding="utf-8", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=["call_id", "item", "gold",
                                                      "pred", "correct"])
                    w.writeheader()
                    w.writerows(items)
                print(f"  → {OUT_ITEMS}")

    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"→ {OUT}")

    print("\n=== Средние по уровню WER ===")
    by_level: dict[float, list[dict]] = {}
    for r in rows:
        by_level.setdefault(r["target_wer"], []).append(r)
    print(f"{'target':>7} {'actual':>7} {'check_acc':>10} {'fact_f1':>8} {'outcome':>8} {'rouge_l':>8}")
    for lvl in WER_LEVELS:
        g = by_level[lvl]
        avg = lambda k: sum(x[k] for x in g) / len(g)
        print(f"{lvl:7.2f} {avg('actual_wer'):7.3f} {avg('checklist_accuracy'):10.3f} "
              f"{avg('fact_f1'):8.3f} {avg('outcome_accuracy'):8.3f} {avg('summary_rouge_l'):8.3f}")


if __name__ == "__main__":
    args = sys.argv[1:]
    model = next((a for a in args if not a.isdigit()), "local_qwen_1_5b")
    seeds = next((int(a) for a in args if a.isdigit()), 2)
    main(model, seeds)
