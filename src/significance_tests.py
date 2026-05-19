from __future__ import annotations

import csv
import json
import random
from collections import defaultdict
from pathlib import Path

from jiwer import wer as jiwer_wer

from src.metrics import mcnemar_exact

OUT = Path("results/significance_tests.json")


def paired_bootstrap_asr(model_a: str, model_b: str, n_iter: int = 2000,
                         seed: int = 42) -> dict:
    rows = defaultdict(dict)
    with open("results/asr_raw_results.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["model_name"] in (model_a, model_b) and not r.get("error"):
                rows[r["audio_path"]][r["model_name"]] = (
                    (r.get("reference_norm") or "").strip(),
                    (r.get("hypothesis_norm") or "").strip(),
                )
    paired = [(v[model_a], v[model_b]) for v in rows.values()
              if model_a in v and model_b in v]
    n = len(paired)
    if n == 0:
        return {"error": f"нет общих файлов для {model_a} и {model_b}"}

    def corpus_wer(pairs, idx, which):
        ref = " ".join(pairs[i][which][0] for i in idx)
        hyp = " ".join(pairs[i][which][1] for i in idx)
        return jiwer_wer(ref, hyp) if ref.strip() else 0.0

    full = list(range(n))
    wer_a = corpus_wer(paired, full, 0)
    wer_b = corpus_wer(paired, full, 1)
    point_diff = wer_b - wer_a

    rng = random.Random(seed)
    diffs = []
    for _ in range(n_iter):
        idx = [rng.randrange(n) for _ in range(n)]
        diffs.append(corpus_wer(paired, idx, 1) - corpus_wer(paired, idx, 0))
    diffs.sort()
    lo = diffs[int(n_iter * 0.025)]
    hi = diffs[int(n_iter * 0.975)]
    p_one_sided = sum(1 for d in diffs if d <= 0) / n_iter
    return {
        "model_a": model_a, "model_b": model_b, "n_paired_files": n,
        f"wer_{model_a}": round(wer_a, 4),
        f"wer_{model_b}": round(wer_b, 4),
        "diff_b_minus_a": round(point_diff, 4),
        "diff_95ci": [round(lo, 4), round(hi, 4)],
        "ci_includes_zero": lo <= 0 <= hi,
        "p_value_one_sided": round(p_one_sided, 4),
        "significant_at_0.05": not (lo <= 0 <= hi),
    }


def mcnemar_sentiment(col_a: str, col_b: str) -> dict:
    with open("results/sentiment_raw.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    b = c = both_ok = both_wrong = 0
    for r in rows:
        gold = r["label"]
        a_ok = r[col_a] == gold
        b_ok = r[col_b] == gold
        if a_ok and not b_ok:
            b += 1
        elif not a_ok and b_ok:
            c += 1
        elif a_ok and b_ok:
            both_ok += 1
        else:
            both_wrong += 1
    p = mcnemar_exact(b, c)
    return {
        "model_a": col_a.replace("pred_", ""),
        "model_b": col_b.replace("pred_", ""),
        "n": len(rows),
        "both_correct": both_ok, "both_wrong": both_wrong,
        "only_a_correct": b, "only_b_correct": c,
        "discordant_pairs": b + c,
        "p_value": round(p, 5),
        "significant_at_0.05": p < 0.05,
    }


def main() -> None:
    Path("results").mkdir(exist_ok=True)
    result = {}

    print("=" * 60)
    print("1. ASR — парный bootstrap T-one vs GigaAM")
    asr = paired_bootstrap_asr("T-one", "GigaAM", n_iter=2000)
    result["asr_tone_vs_gigaam"] = asr
    if "error" not in asr:
        print(f"  n общих файлов: {asr['n_paired_files']}")
        print(f"  WER T-one={asr['wer_T-one']}  GigaAM={asr['wer_GigaAM']}")
        print(f"  разница (GigaAM−T-one) = {asr['diff_b_minus_a']:+.4f}")
        print(f"  95% CI разницы: {asr['diff_95ci']}")
        print(f"  CI включает 0: {asr['ci_includes_zero']}")
        print(f"  → различие {'ЗНАЧИМО' if asr['significant_at_0.05'] else 'НЕ значимо'} "
              f"на уровне 0.05")

    print("\n" + "=" * 60)
    print("2. Sentiment — McNemar")
    with open("results/sentiment_raw.csv", encoding="utf-8") as f:
        cols = [c for c in next(csv.reader(f)) if c.startswith("pred_")]
    xlm = next((c for c in cols if "xlm" in c), None)
    rubert = next((c for c in cols if "rubert" in c), None)
    tab = next((c for c in cols if "tabular" in c), None)
    pairs = []
    if xlm and rubert:
        pairs.append((xlm, rubert))
    if xlm and tab:
        pairs.append((xlm, tab))
    result["sentiment_mcnemar"] = []
    for a, b in pairs:
        m = mcnemar_sentiment(a, b)
        result["sentiment_mcnemar"].append(m)
        print(f"\n  {m['model_a']} vs {m['model_b']} (n={m['n']}):")
        print(f"    только A верна: {m['only_a_correct']}, "
              f"только B верна: {m['only_b_correct']}")
        print(f"    p-value = {m['p_value']}  → "
              f"{'ЗНАЧИМО' if m['significant_at_0.05'] else 'НЕ значимо'}")

    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n→ {OUT}")


if __name__ == "__main__":
    main()
