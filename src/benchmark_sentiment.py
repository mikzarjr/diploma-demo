import time
from datasets import load_dataset
import pandas as pd
from sklearn.metrics import classification_report, f1_score, accuracy_score
from tqdm import tqdm
from pathlib import Path

from src.models.sentiment_runners import (
    transcribe_sentiment_rubert_tiny,
    transcribe_sentiment_rubert_base,
    transcribe_sentiment_xlm,
)

N_SAMPLES = 300
RESULTS_DIR = Path("results")

LABEL_MAP = {"negative": 0, "neutral": 1, "positive": 2}
CLASSES = ["negative", "neutral", "positive"]

_POS_EMOTIONS = {
    "admiration", "amusement", "approval", "caring", "desire", "excitement",
    "gratitude", "joy", "love", "optimism", "pride", "relief",
}
_NEG_EMOTIONS = {
    "anger", "annoyance", "disappointment", "disapproval", "disgust",
    "embarrassment", "fear", "grief", "nervousness", "remorse", "sadness",
}


def _map_goemotion_to_sentiment(row) -> str:
    pos = sum(row.get(e, 0) for e in _POS_EMOTIONS)
    neg = sum(row.get(e, 0) for e in _NEG_EMOTIONS)
    if row.get("neutral", 0) and pos == 0 and neg == 0:
        return "neutral"
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"


def load_test_data(n_per_class: int = N_SAMPLES) -> pd.DataFrame:
    ds = load_dataset("seara/ru_go_emotions", "raw", split="train")
    df = ds.to_pandas()
    df = df.drop(columns=["text"], errors="ignore")
    df = df.rename(columns={"ru_text": "text"})
    df["label"] = df.apply(_map_goemotion_to_sentiment, axis=1)
    df = df[["text", "label"]].dropna(subset=["text", "label"])
    df["text"] = df["text"].astype(str)

    parts = []
    for cls in CLASSES:
        sub = df[df["label"] == cls]
        parts.append(sub.sample(min(n_per_class, len(sub)), random_state=42))
    return pd.concat(parts, ignore_index=True).sample(frac=1, random_state=42)


def evaluate_model(name: str, predict_fn, df: pd.DataFrame) -> dict:
    preds, golds, latencies = [], [], []
    errors = 0
    for _, row in tqdm(df.iterrows(), total=len(df), desc=name):
        t0 = time.perf_counter()
        try:
            pred = predict_fn(row["text"])
            latency = time.perf_counter() - t0
            preds.append(pred)
            golds.append(row["label"])
            latencies.append(latency)
        except Exception:
            errors += 1
            latencies.append(time.perf_counter() - t0)

    f1 = f1_score(golds, preds, average="weighted", labels=CLASSES, zero_division=0)
    acc = accuracy_score(golds, preds)

    return {
        "model": name,
        "n": len(preds),
        "errors": errors,
        "accuracy": round(acc, 4),
        "f1_weighted": round(f1, 4),
        "avg_latency_ms": round(sum(latencies) / len(latencies) * 1000, 1),
        "report": classification_report(golds, preds, labels=CLASSES, zero_division=0),
        "golds": golds,
        "preds": preds,
    }


def main():
    print("Loading dataset...")
    df = load_test_data()
    print(f"Test set: {len(df)} samples — {df['label'].value_counts().to_dict()}")

    models = {
        "rubert-tiny2 (seara)": transcribe_sentiment_rubert_tiny,
        "multilingual-tabularisai": transcribe_sentiment_rubert_base,
        "xlm-roberta-multilingual (cardiffnlp)": transcribe_sentiment_xlm,
    }

    RESULTS_DIR.mkdir(exist_ok=True)
    all_rows = []
    all_preds = {}

    for name, fn in models.items():
        result = evaluate_model(name, fn, df)
        all_rows.append({k: v for k, v in result.items() if k not in ("report", "golds", "preds")})
        all_preds[name] = result["preds"]
        print(f"\n--- {name} ---")
        print(result["report"])

    summary_df = pd.DataFrame(all_rows).sort_values("f1_weighted", ascending=False)
    summary_df.to_csv(RESULTS_DIR / "sentiment_summary.csv", index=False)

    raw_df = df[["text", "label"]].copy()
    for name, preds in all_preds.items():
        raw_df[f"pred_{name.replace('-', '_')}"] = preds
    raw_df.to_csv(RESULTS_DIR / "sentiment_raw.csv", index=False)

    print("\n=== SENTIMENT SUMMARY ===")
    print(summary_df[["model", "n", "accuracy", "f1_weighted", "avg_latency_ms", "errors"]].to_string(index=False))


if __name__ == "__main__":
    main()
