from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

from src.benchmark_sentiment import CLASSES
from src.finetune_sentiment import load_3class, evaluate, LABEL2ID, ID2LABEL, MODELS

MODEL_KEY = "rubert_tiny"
TRAIN_SIZES = [1000, 2000, 4000, 8000, 16000, 36000]
N_SEEDS = 2
EPOCHS = 3
BASELINE_F1 = 0.510

OUT_CSV = Path("results/learning_curve.csv")
OUT_PNG = Path("results/learning_curve.png")


def build_test(df: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for cls in CLASSES:
        sub = df[df["label"] == cls]
        parts.append(sub.sample(min(300, len(sub)), random_state=42))
    return pd.concat(parts).sample(frac=1, random_state=42).reset_index(drop=True)


def sample_train(df: pd.DataFrame, test_texts: set, total_size: int,
                 seed: int) -> pd.DataFrame:
    pool_all = df[~df["text"].isin(test_texts)].drop_duplicates(subset="text")
    per_class = total_size // len(CLASSES)
    parts = []
    for cls in CLASSES:
        pool = pool_all[pool_all["label"] == cls]
        parts.append(pool.sample(min(per_class, len(pool)), random_state=seed))
    return pd.concat(parts).sample(frac=1, random_state=seed).reset_index(drop=True)


def finetune_and_eval(train_df: pd.DataFrame, test_df: pd.DataFrame,
                      seed: int) -> float:
    import torch
    from transformers import (AutoTokenizer, AutoModelForSequenceClassification,
                              TrainingArguments, Trainer, DataCollatorWithPadding)
    from datasets import Dataset

    model_id = MODELS[MODEL_KEY]
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_id, num_labels=3, id2label=ID2LABEL, label2id=LABEL2ID,
        ignore_mismatched_sizes=True,
    ).to(device)

    ds = Dataset.from_dict({
        "text": train_df["text"].tolist(),
        "labels": [LABEL2ID[x] for x in train_df["label"]],
    }).map(lambda b: tokenizer(b["text"], truncation=True, max_length=128),
           batched=True)

    args = TrainingArguments(
        output_dir=f"models_finetuned/_lc_{seed}",
        num_train_epochs=EPOCHS, per_device_train_batch_size=16,
        learning_rate=2e-5, logging_strategy="no", save_strategy="no",
        report_to=[], seed=seed,
    )
    collator = DataCollatorWithPadding(tokenizer)
    try:
        trainer = Trainer(model=model, args=args, train_dataset=ds,
                          data_collator=collator, processing_class=tokenizer)
    except TypeError:
        trainer = Trainer(model=model, args=args, train_dataset=ds,
                          data_collator=collator, tokenizer=tokenizer)
    trainer.train()
    f1 = evaluate(model, tokenizer, test_df, device)["f1_weighted"]

    import gc
    import shutil
    del model, trainer
    gc.collect()
    if device == "mps":
        torch.mps.empty_cache()
    shutil.rmtree(f"models_finetuned/_lc_{seed}", ignore_errors=True)
    return f1


def plot(curve: list[dict]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    sizes = sorted({r["train_size"] for r in curve})
    means = [sum(r["f1"] for r in curve if r["train_size"] == s) /
             sum(1 for r in curve if r["train_size"] == s) for s in sizes]
    mins = [min(r["f1"] for r in curve if r["train_size"] == s) for s in sizes]
    maxs = [max(r["f1"] for r in curve if r["train_size"] == s) for s in sizes]

    fig, ax = plt.subplots(figsize=(8, 5))
    yerr = [[m - lo for m, lo in zip(means, mins)],
            [hi - m for m, hi in zip(means, maxs)]]
    ax.errorbar(sizes, means, yerr=yerr, marker="o", capsize=4,
                color="#0969da", label="rubert-tiny2 дообученная")
    ax.axhline(BASELINE_F1, color="#d1242f", linestyle="--",
               label=f"rubert-tiny2 без дообучения (F1={BASELINE_F1})")
    ax.axhline(0.556, color="#1a7f37", linestyle=":",
               label="xlm-roberta без дообучения (F1=0.556)")
    for s, m in zip(sizes, means):
        ax.annotate(f"{m:.3f}", (s, m), textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=9)
    ax.set_xlabel("Объём обучающей выборки (примеров)")
    ax.set_ylabel("weighted F1 на тесте (900 примеров)")
    ax.set_title("Кривая обучения: дообучение rubert-tiny2 на sentiment-задаче")
    ax.legend(loc="lower right", fontsize=9)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=130)
    print(f"→ {OUT_PNG}")


def main() -> None:
    df = load_3class()
    test_df = build_test(df)
    test_texts = set(test_df["text"])
    print(f"Тест: {len(test_df)} примеров. Кривая обучения по размерам {TRAIN_SIZES}, "
          f"{N_SEEDS} seed(ов) на точку.")

    curve = []
    for size in TRAIN_SIZES:
        for seed in range(1, N_SEEDS + 1):
            train_df = sample_train(df, test_texts, size, seed)
            t0 = time.perf_counter()
            f1 = finetune_and_eval(train_df, test_df, seed)
            dt = time.perf_counter() - t0
            curve.append({"train_size": len(train_df), "seed": seed,
                          "f1": round(f1, 4)})
            print(f"  train={len(train_df):5d} seed={seed}: F1={f1:.4f} ({dt:.0f} с)")

    Path("results").mkdir(exist_ok=True)
    pd.DataFrame(curve).to_csv(OUT_CSV, index=False)
    print(f"→ {OUT_CSV}")
    plot(curve)

    print("\n=== Кривая обучения (среднее по seed'ам) ===")
    print(f"{'train':>7} {'F1':>8}  Δ к baseline")
    for size in sorted({r["train_size"] for r in curve}):
        vals = [r["f1"] for r in curve if r["train_size"] == size]
        mean = sum(vals) / len(vals)
        print(f"{size:7d} {mean:8.4f}  {mean - BASELINE_F1:+.4f}")
    print(f"baseline (0 примеров): {BASELINE_F1}")


if __name__ == "__main__":
    main()
