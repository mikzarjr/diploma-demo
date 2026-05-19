from __future__ import annotations

import argparse
import random
import time
import wave
from dataclasses import dataclass, asdict
from typing import Callable, Dict, List, Optional

import pandas as pd
from jiwer import cer
from tqdm import tqdm

from src.metrics import normalize_text, bootstrap_wer_ci

from src.models.yandex_runner import transcribe_yandex
from src.models.deepgram_runner import transcribe_deepgram
from src.models.t_one_runner import transcribe_t_one

try:
    from src.models.gigaam_runner import transcribe_gigaam

    GIGAAM_AVAILABLE = True
except ImportError:
    GIGAAM_AVAILABLE = False

MANIFEST_PATH = "data/manifests/asr_calls_2_val_manifest.tsv"


def load_manifest(path: str) -> pd.DataFrame:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            audio_path, ref = line.rstrip("\n").split("\t", 1)
            rows.append({
                "audio_path": audio_path,
                "reference": ref,
                "reference_norm": normalize_text(ref),
            })
    return pd.DataFrame(rows)


def sample_files(df: pd.DataFrame, n: int, seed: int) -> pd.DataFrame:
    rng = random.Random(seed)
    idxs = list(range(len(df)))
    rng.shuffle(idxs)
    return df.iloc[idxs[:n]].reset_index(drop=True)


@dataclass
class SampleResult:
    model_name: str
    audio_path: str
    reference: str
    hypothesis: str
    reference_norm: str
    hypothesis_norm: str
    latency_sec: float
    audio_duration_sec: Optional[float]
    error: Optional[str] = None


def get_wav_duration_sec(audio_path: str) -> Optional[float]:
    try:
        with wave.open(audio_path, "rb") as wf:
            return wf.getnframes() / float(wf.getframerate())
    except Exception:
        return None


def compute_summary(df: pd.DataFrame, n_bootstrap: int = 1000) -> pd.DataFrame:
    rows = []
    for model_name, group in df.groupby("model_name"):
        valid = group[group["error"].isna()].copy()
        valid["reference_norm"] = valid["reference_norm"].fillna("")
        valid["hypothesis_norm"] = valid["hypothesis_norm"].fillna("")

        if valid.empty:
            rows.append({
                "model_name": model_name, "n": 0,
                "wer": None, "wer_ci_low": None, "wer_ci_high": None,
                "cer": None, "avg_latency_sec": None, "avg_rtf": None,
                "errors": int(group["error"].notna().sum()),
            })
            continue

        refs = [str(x) for x in valid["reference_norm"].tolist()]
        hyps = [str(x) for x in valid["hypothesis_norm"].tolist()]

        wer_point, wer_lo, wer_hi = bootstrap_wer_ci(refs, hyps, n_iter=n_bootstrap)
        cer_val = cer(" ".join(refs), " ".join(hyps))

        valid["rtf"] = valid.apply(
            lambda x: x["latency_sec"] / x["audio_duration_sec"]
            if x["audio_duration_sec"] and x["audio_duration_sec"] > 0 else None,
            axis=1,
        )

        rows.append({
            "model_name": model_name,
            "n": len(valid),
            "wer": round(wer_point, 4),
            "wer_ci_low": round(wer_lo, 4),
            "wer_ci_high": round(wer_hi, 4),
            "wer_ci_width_pp": round((wer_hi - wer_lo) * 100, 2),
            "cer": round(cer_val, 4),
            "avg_latency_sec": round(valid["latency_sec"].mean(), 3),
            "avg_rtf": round(valid["rtf"].dropna().mean(), 3),
            "errors": int(group["error"].notna().sum()),
        })

    return pd.DataFrame(rows).sort_values("wer", ascending=True)


def run_model(df: pd.DataFrame, model_name: str, transcribe_fn: Callable[[str], str]) -> List[SampleResult]:
    results = []
    for _, row in tqdm(df.iterrows(), total=len(df), desc=model_name):
        audio_path = row["audio_path"]
        reference = row["reference"]
        reference_norm = row["reference_norm"]
        start = time.perf_counter()
        try:
            hypothesis = transcribe_fn(audio_path)
            latency = time.perf_counter() - start
            duration = get_wav_duration_sec(audio_path)
            results.append(SampleResult(
                model_name=model_name, audio_path=audio_path,
                reference=reference, hypothesis=hypothesis,
                reference_norm=reference_norm,
                hypothesis_norm=normalize_text(hypothesis),
                latency_sec=latency, audio_duration_sec=duration,
                error=None,
            ))
        except Exception as e:
            latency = time.perf_counter() - start
            duration = get_wav_duration_sec(audio_path)
            results.append(SampleResult(
                model_name=model_name, audio_path=audio_path,
                reference=reference, hypothesis="",
                reference_norm=reference_norm, hypothesis_norm="",
                latency_sec=latency, audio_duration_sec=duration,
                error=str(e),
            ))
    return results


def build_registry(selected: Optional[List[str]]) -> Dict[str, Callable[[str], str]]:
    available = {"yandex": ("Yandex SpeechKit", transcribe_yandex),
                 "deepgram": ("Deepgram Nova-3", transcribe_deepgram),
                 "t_one": ("T-one", transcribe_t_one)}
    if GIGAAM_AVAILABLE:
        available["gigaam"] = ("GigaAM", transcribe_gigaam)
    if not selected:
        return {label: fn for label, fn in available.values()}
    chosen = {}
    for key in selected:
        if key not in available:
            print(f"⚠️  Unknown model: {key} (available: {list(available)})")
            continue
        label, fn = available[key]
        chosen[label] = fn
    return chosen


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--models", type=str, default="",
                        help="comma-separated: t_one,gigaam,yandex,deepgram")
    parser.add_argument("--bootstrap", type=int, default=1000)
    parser.add_argument("--raw-out", default="results/asr_raw_results.csv")
    parser.add_argument("--summary-out", default="results/asr_summary.csv")
    args = parser.parse_args()

    df = load_manifest(MANIFEST_PATH)
    print(f"Manifest: {len(df)} files. Sampling {args.n} with seed={args.seed}.")
    df = sample_files(df, args.n, args.seed)

    selected = [s.strip() for s in args.models.split(",") if s.strip()] or None
    registry = build_registry(selected)
    print(f"Models to run: {list(registry)}")

    all_results: List[SampleResult] = []
    for model_name, fn in registry.items():
        model_results = run_model(df, model_name, fn)
        all_results.extend(model_results)

    result_df = pd.DataFrame([asdict(x) for x in all_results])

    import os
    if os.path.exists(args.raw_out):
        try:
            existing = pd.read_csv(args.raw_out)
            new_models = set(result_df["model_name"].unique())
            keep = existing[~existing["model_name"].isin(new_models)]
            combined = pd.concat([keep, result_df], ignore_index=True)
        except Exception as e:
            print(f"  ! не удалось дочитать {args.raw_out}: {e}; перезаписываю")
            combined = result_df
    else:
        combined = result_df
    combined.to_csv(args.raw_out, index=False)

    summary_df = compute_summary(combined, n_bootstrap=args.bootstrap)
    summary_df.to_csv(args.summary_out, index=False)

    print("\n=== SUMMARY ===")
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()
