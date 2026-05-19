from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

import jiwer

from src.metrics import pearson

OUT = Path("results/error_analysis.json")

FILLERS = {"эээ", "ээ", "э", "ааа", "аа", "мм", "ну", "вот", "это",
           "значит", "короче", "типа"}


def filler_ratio(text: str) -> float:
    toks = re.findall(r"[а-яё]+", (text or "").lower())
    if not toks:
        return 0.0
    return sum(1 for t in toks if t in FILLERS) / len(toks)


def analyze_asr() -> dict:
    rows = []
    with open("results/asr_raw_results.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    out = {}
    by_model = defaultdict(list)
    for r in rows:
        by_model[r["model_name"]].append(r)

    for model, recs in by_model.items():
        S = D = I = H = 0
        per_file = []
        for r in recs:
            ref = (r.get("reference_norm") or "").strip()
            hyp = (r.get("hypothesis_norm") or "").strip()
            if not ref:
                continue
            m = jiwer.process_words(ref, hyp)
            S += m.substitutions
            D += m.deletions
            I += m.insertions
            H += m.hits
            n_ref = m.substitutions + m.deletions + m.hits
            file_wer = (m.substitutions + m.deletions + m.insertions) / n_ref if n_ref else 0.0
            dur = r.get("audio_duration_sec")
            per_file.append({
                "audio_path": r["audio_path"],
                "wer": file_wer,
                "duration": float(dur) if dur else None,
                "filler_ratio": filler_ratio(r.get("reference", "")),
                "n_ref_words": n_ref,
            })
        total_err = S + D + I
        worst = sorted(per_file, key=lambda x: x["wer"], reverse=True)[:10]
        durs = [(p["wer"], p["duration"]) for p in per_file if p["duration"]]
        fills = [(p["wer"], p["filler_ratio"]) for p in per_file]
        out[model] = {
            "n_files": len(per_file),
            "error_breakdown": {
                "substitutions": S, "deletions": D, "insertions": I,
                "sub_pct": round(100 * S / total_err, 1) if total_err else 0,
                "del_pct": round(100 * D / total_err, 1) if total_err else 0,
                "ins_pct": round(100 * I / total_err, 1) if total_err else 0,
            },
            "corr_wer_vs_duration": round(
                pearson([d[0] for d in durs], [d[1] for d in durs]), 3),
            "corr_wer_vs_filler_ratio": round(
                pearson([f[0] for f in fills], [f[1] for f in fills]), 3),
            "share_perfect_files": round(
                sum(1 for p in per_file if p["wer"] == 0) / len(per_file), 3)
            if per_file else 0,
            "share_files_wer_over_0.5": round(
                sum(1 for p in per_file if p["wer"] > 0.5) / len(per_file), 3)
            if per_file else 0,
            "top10_worst_wer": [round(w["wer"], 3) for w in worst],
        }
    return out


CLASSES = ["negative", "neutral", "positive"]


def analyze_sentiment() -> dict:
    with open("results/sentiment_raw.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return {}
    pred_cols = [c for c in rows[0].keys() if c.startswith("pred_")]
    out = {}
    for col in pred_cols:
        cm = {g: {p: 0 for p in CLASSES} for g in CLASSES}
        for r in rows:
            g = r["label"]
            p = r[col]
            if g in cm and p in cm[g]:
                cm[g][p] += 1
        per_class = {}
        for c in CLASSES:
            tp = cm[c][c]
            fp = sum(cm[g][c] for g in CLASSES if g != c)
            fn = sum(cm[c][p] for p in CLASSES if p != c)
            prec = tp / (tp + fp) if (tp + fp) else 0.0
            rec = tp / (tp + fn) if (tp + fn) else 0.0
            per_class[c] = {
                "precision": round(prec, 3), "recall": round(rec, 3),
                "f1": round(2 * prec * rec / (prec + rec), 3) if (prec + rec) else 0.0,
            }
        confusions = [((g, p), cm[g][p]) for g in CLASSES for p in CLASSES if g != p]
        confusions.sort(key=lambda x: x[1], reverse=True)
        out[col.replace("pred_", "")] = {
            "confusion_matrix": cm,
            "per_class": per_class,
            "top_confusion": {
                "gold→pred": f"{confusions[0][0][0]}→{confusions[0][0][1]}",
                "count": confusions[0][1],
            },
        }
    return out


def analyze_llm() -> dict:
    path = Path("results/ablation_asr_baseline_items.csv")
    if not path.exists():
        return {"note": "ablation_asr_baseline_items.csv ещё не создан "
                        "(запусти src/ablation_asr_propagation.py)"}
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    by_item = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "tn": 0})
    for r in rows:
        g, p = int(r["gold"]), int(r["pred"])
        d = by_item[r["item"]]
        if g == 1 and p == 1:
            d["tp"] += 1
        elif g == 0 and p == 1:
            d["fp"] += 1
        elif g == 1 and p == 0:
            d["fn"] += 1
        else:
            d["tn"] += 1
    out = {}
    for item, d in by_item.items():
        prec = d["tp"] / (d["tp"] + d["fp"]) if (d["tp"] + d["fp"]) else 0.0
        rec = d["tp"] / (d["tp"] + d["fn"]) if (d["tp"] + d["fn"]) else 0.0
        out[item] = {
            **d,
            "precision": round(prec, 3),
            "recall": round(rec, 3),
            "f1": round(2 * prec * rec / (prec + rec), 3) if (prec + rec) else 0.0,
            "error_type": ("много ложных true (FP)" if d["fp"] > d["fn"]
                           else "много пропусков true (FN)" if d["fn"] > d["fp"]
            else "сбалансировано"),
        }
    return out


def main() -> None:
    Path("results").mkdir(exist_ok=True)
    result = {
        "asr": analyze_asr(),
        "sentiment": analyze_sentiment(),
        "llm_checklist": analyze_llm(),
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 60)
    print("ASR — разбивка ошибок")
    for model, d in result["asr"].items():
        eb = d["error_breakdown"]
        print(f"\n{model} (n={d['n_files']}):")
        print(f"  S/D/I: {eb['sub_pct']}% / {eb['del_pct']}% / {eb['ins_pct']}%")
        print(f"  corr(WER, длительность) = {d['corr_wer_vs_duration']}")
        print(f"  corr(WER, filler-ratio) = {d['corr_wer_vs_filler_ratio']}")
        print(f"  идеальных файлов (WER=0): {d['share_perfect_files'] * 100:.1f}%, "
              f"WER>0.5: {d['share_files_wer_over_0.5'] * 100:.1f}%")

    print("\n" + "=" * 60)
    print("SENTIMENT — confusion")
    for model, d in result["sentiment"].items():
        print(f"\n{model}:")
        print(f"  топ-путаница: {d['top_confusion']['gold→pred']} "
              f"({d['top_confusion']['count']} раз)")
        for c, pc in d["per_class"].items():
            print(f"  {c:9}: P={pc['precision']} R={pc['recall']} F1={pc['f1']}")

    print("\n" + "=" * 60)
    print("LLM — per-item чек-лист")
    llm = result["llm_checklist"]
    if "note" in llm:
        print(f"  {llm['note']}")
    else:
        for item, d in sorted(llm.items(), key=lambda x: x[1]["f1"]):
            print(f"  {item:20} F1={d['f1']:.2f}  TP={d['tp']} FP={d['fp']} "
                  f"FN={d['fn']} TN={d['tn']}  → {d['error_type']}")
    print(f"\n→ {OUT}")


if __name__ == "__main__":
    main()
