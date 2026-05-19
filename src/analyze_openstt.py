from __future__ import annotations

import json
import random
import re
import wave
from collections import Counter
from pathlib import Path
from statistics import mean, quantiles

MANIFEST = Path("data/manifests/asr_calls_2_val_manifest.tsv")
OUT_DIR = Path("results")
OUT_DIR.mkdir(exist_ok=True)

FILLERS = {"эээ", "ээ", "э", "ааа", "аа", "а-а", "мм", "м-м", "ну", "вот", "это",
           "значит", "короче", "типа", "как-бы", "ну-ну"}

LATIN = re.compile(r"[a-z]+", re.IGNORECASE)


def load_manifest() -> list[tuple[str, str]]:
    rows = []
    with MANIFEST.open(encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            wav, _, text = line.partition("\t")
            rows.append((wav, text))
    return rows


def wav_info(path: str) -> dict | None:
    try:
        with wave.open(path, "rb") as w:
            frames = w.getnframes()
            sr = w.getframerate()
            n_ch = w.getnchannels()
            sw = w.getsampwidth()
            return {
                "duration_sec": frames / sr if sr else 0.0,
                "sample_rate": sr,
                "n_channels": n_ch,
                "sample_width_bytes": sw,
                "frames": frames,
            }
    except Exception as exc:
        return {"error": str(exc)}


def text_features(text: str) -> dict:
    raw = text.strip()
    norm = raw.lower().replace("ё", "е")
    tokens = re.findall(r"[а-яa-z0-9]+", norm)
    fillers = [t for t in tokens if t in FILLERS]
    latin_tokens = [t for t in tokens if LATIN.fullmatch(t)]
    return {
        "char_len": len(raw),
        "n_tokens": len(tokens),
        "n_fillers": len(fillers),
        "filler_ratio": len(fillers) / len(tokens) if tokens else 0.0,
        "n_latin_tokens": len(latin_tokens),
        "has_latin": len(latin_tokens) > 0,
        "tokens": tokens,
    }


def hash_prefix(path: str) -> str:
    parts = Path(path).parts
    try:
        i = parts.index("asr_calls_2_val")
        return "/".join(parts[i + 1: i + 3])
    except ValueError:
        return ""


def main(audio_sample: int = 500, text_sample: int = 5000, seed: int = 42) -> None:
    rows = load_manifest()
    print(f"Manifest entries: {len(rows)}")

    rng = random.Random(seed)
    rng.shuffle(rows)

    audio_rows = []
    durations: list[float] = []
    sample_rates: Counter[int] = Counter()
    channels: Counter[int] = Counter()
    sample_widths: Counter[int] = Counter()

    for wav, text in rows[:audio_sample]:
        info = wav_info(wav)
        if info is None or "error" in info:
            continue
        durations.append(info["duration_sec"])
        sample_rates[info["sample_rate"]] += 1
        channels[info["n_channels"]] += 1
        sample_widths[info["sample_width_bytes"]] += 1
        audio_rows.append({"path": wav, **info})

    text_rows = []
    char_lens: list[int] = []
    tok_lens: list[int] = []
    filler_ratios: list[float] = []
    latin_count = 0
    vocab: Counter[str] = Counter()
    prefix_counts: Counter[str] = Counter()

    for wav, text in rows[:text_sample]:
        feats = text_features(text)
        char_lens.append(feats["char_len"])
        tok_lens.append(feats["n_tokens"])
        filler_ratios.append(feats["filler_ratio"])
        if feats["has_latin"]:
            latin_count += 1
        vocab.update(feats["tokens"])
        prefix_counts[hash_prefix(wav)] += 1
        text_rows.append({
            "path": wav,
            "text": text,
            "char_len": feats["char_len"],
            "n_tokens": feats["n_tokens"],
            "n_fillers": feats["n_fillers"],
            "filler_ratio": round(feats["filler_ratio"], 4),
            "n_latin_tokens": feats["n_latin_tokens"],
        })

    def quartiles(xs: list[float]) -> dict:
        if not xs:
            return {}
        if len(xs) < 4:
            return {"min": min(xs), "max": max(xs), "mean": mean(xs)}
        q = quantiles(xs, n=4)
        return {
            "min": round(min(xs), 3),
            "q1": round(q[0], 3),
            "median": round(q[1], 3),
            "q3": round(q[2], 3),
            "max": round(max(xs), 3),
            "mean": round(mean(xs), 3),
        }

    summary = {
        "total_files_in_manifest": len(rows),
        "audio_sample_analyzed": len(audio_rows),
        "text_sample_analyzed": len(text_rows),
        "audio": {
            "duration_sec": quartiles(durations),
            "total_duration_hours_extrapolated": round(
                mean(durations) * len(rows) / 3600.0, 1
            ) if durations else None,
            "sample_rate_hist": dict(sample_rates.most_common()),
            "channels_hist": dict(channels.most_common()),
            "sample_width_bytes_hist": dict(sample_widths.most_common()),
        },
        "text": {
            "char_len": quartiles([float(x) for x in char_lens]),
            "n_tokens": quartiles([float(x) for x in tok_lens]),
            "filler_ratio": quartiles(filler_ratios),
            "share_with_latin_token": round(latin_count / len(text_rows), 4)
            if text_rows
            else None,
            "vocabulary_size_in_sample": len(vocab),
            "top_20_tokens": vocab.most_common(20),
        },
        "directory_balance": {
            "n_prefixes": len(prefix_counts),
            "min_files_per_prefix": min(prefix_counts.values()) if prefix_counts else 0,
            "max_files_per_prefix": max(prefix_counts.values()) if prefix_counts else 0,
            "mean_files_per_prefix": round(
                mean(prefix_counts.values()), 2
            ) if prefix_counts else 0.0,
        },
    }

    with (OUT_DIR / "openstt_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    import csv
    with (OUT_DIR / "openstt_audio_stats.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "path", "duration_sec", "sample_rate", "n_channels",
            "sample_width_bytes", "frames",
        ])
        w.writeheader()
        for r in audio_rows:
            w.writerow(r)

    with (OUT_DIR / "openstt_text_stats.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "path", "text", "char_len", "n_tokens", "n_fillers",
            "filler_ratio", "n_latin_tokens",
        ])
        w.writeheader()
        for r in text_rows:
            w.writerow(r)

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
