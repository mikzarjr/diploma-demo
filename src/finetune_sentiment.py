from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pandas as pd
from datasets import Dataset, load_dataset
from sklearn.metrics import f1_score, accuracy_score, classification_report

from src.benchmark_sentiment import _map_goemotion_to_sentiment, CLASSES

LABEL2ID = {"negative": 0, "neutral": 1, "positive": 2}
ID2LABEL = {v: k for k, v in LABEL2ID.items()}

_LABEL_NORM = {
    "negative": "negative", "neutral": "neutral", "positive": "positive",
    "NEGATIVE": "negative", "NEUTRAL": "neutral", "POSITIVE": "positive",
    "Negative": "negative", "Neutral": "neutral", "Positive": "positive",
    "LABEL_0": "negative", "LABEL_1": "neutral", "LABEL_2": "positive",
}

MODELS = {
    "rubert_tiny": "seara/rubert-tiny2-russian-sentiment",
    "xlm_roberta": "cardiffnlp/twitter-xlm-roberta-base-sentiment-multilingual",
}

RESULTS_CSV = Path("results/finetune_sentiment.csv")


def load_3class() -> pd.DataFrame:
    ds = load_dataset("seara/ru_go_emotions", "raw", split="train")
    df = ds.to_pandas()
    df = df.drop(columns=["text"], errors="ignore").rename(columns={"ru_text": "text"})
    df["label"] = df.apply(_map_goemotion_to_sentiment, axis=1)
    df = df[["text", "label"]].dropna()
    df["text"] = df["text"].astype(str)
    return df.reset_index(drop=True)


def split_train_test(df: pd.DataFrame, n_train_per_class: int,
                     n_test_per_class: int = 300) -> tuple[pd.DataFrame, pd.DataFrame]:
    test_parts = []
    for cls in CLASSES:
        sub = df[df["label"] == cls]
        test_parts.append(sub.sample(min(n_test_per_class, len(sub)), random_state=42))
    test = pd.concat(test_parts).sample(frac=1, random_state=42).reset_index(drop=True)
    test_texts = set(test["text"])

    pool_all = df[~df["text"].isin(test_texts)].drop_duplicates(subset="text")
    train_parts = []
    for cls in CLASSES:
        sub = pool_all[pool_all["label"] == cls]
        train_parts.append(sub.sample(min(n_train_per_class, len(sub)),
                                      random_state=1))
    train = pd.concat(train_parts).sample(frac=1, random_state=1).reset_index(drop=True)

    overlap = set(train["text"]) & test_texts
    print(f"  train={len(train)}  test={len(test)}  пересечение текстов={len(overlap)}")
    assert len(overlap) == 0, "утечка train/test!"
    return train, test


def evaluate(model, tokenizer, df: pd.DataFrame, device) -> dict:
    import torch
    id2label = model.config.id2label
    preds = []
    model.eval()
    for i in range(0, len(df), 32):
        batch = df["text"].iloc[i:i + 32].tolist()
        enc = tokenizer(batch, padding=True, truncation=True, max_length=128,
                        return_tensors="pt").to(device)
        with torch.no_grad():
            logits = model(**enc).logits
        for row in logits.argmax(-1).tolist():
            raw = id2label[row]
            preds.append(_LABEL_NORM.get(raw, str(raw).lower()))
    golds = df["label"].tolist()
    return {
        "accuracy": round(accuracy_score(golds, preds), 4),
        "f1_weighted": round(f1_score(golds, preds, average="weighted",
                                      labels=CLASSES, zero_division=0), 4),
        "report": classification_report(golds, preds, labels=CLASSES,
                                        zero_division=0, digits=3),
    }


def main(model_key: str, n_train_per_class: int = 2000, epochs: int = 3) -> None:
    import torch
    from transformers import (AutoTokenizer, AutoModelForSequenceClassification,
                              TrainingArguments, Trainer, DataCollatorWithPadding)

    if model_key not in MODELS:
        print(f"model_key ∈ {list(MODELS)}")
        return
    model_id = MODELS[model_key]
    if os.getenv("FORCE_CPU") == "1":
        device = "cpu"
    else:
        device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"Fine-tuning {model_key} ({model_id}) на {device}")

    df = load_3class()
    print(f"ru_go_emotions 3-class: {len(df)} строк, {df['label'].value_counts().to_dict()}")
    train_df, test_df = split_train_test(df, n_train_per_class)

    tokenizer = AutoTokenizer.from_pretrained(model_id)

    before_model = AutoModelForSequenceClassification.from_pretrained(model_id).to(device)
    before = evaluate(before_model, tokenizer, test_df, device)
    print(f"\n=== ДО дообучения ===\nF1={before['f1_weighted']}  acc={before['accuracy']}")
    print(before["report"])
    import gc
    del before_model
    gc.collect()
    if device == "mps":
        torch.mps.empty_cache()

    base_model = AutoModelForSequenceClassification.from_pretrained(
        model_id, num_labels=3, id2label=ID2LABEL, label2id=LABEL2ID,
        ignore_mismatched_sizes=True,
    ).to(device)

    def tok(batch):
        return tokenizer(batch["text"], truncation=True, max_length=128)

    train_ds = Dataset.from_dict({
        "text": train_df["text"].tolist(),
        "labels": [LABEL2ID[x] for x in train_df["label"]],
    }).map(tok, batched=True)

    args = TrainingArguments(
        output_dir=f"models_finetuned/_ckpt_{model_key}",
        num_train_epochs=epochs,
        per_device_train_batch_size=4,
        gradient_accumulation_steps=4,
        gradient_checkpointing=True,
        use_cpu=(device == "cpu"),
        learning_rate=2e-5,
        logging_steps=50,
        save_strategy="no",
        report_to=[],
        seed=42,
    )
    base_model.config.use_cache = False
    collator = DataCollatorWithPadding(tokenizer)
    try:
        trainer = Trainer(model=base_model, args=args, train_dataset=train_ds,
                          data_collator=collator, processing_class=tokenizer)
    except TypeError:
        trainer = Trainer(model=base_model, args=args, train_dataset=train_ds,
                          data_collator=collator, tokenizer=tokenizer)
    t0 = time.perf_counter()
    trainer.train()
    train_sec = time.perf_counter() - t0
    print(f"Дообучение заняло {train_sec:.0f} с")

    after = evaluate(base_model, tokenizer, test_df, device)
    print(f"\n=== ПОСЛЕ дообучения ===\nF1={after['f1_weighted']}  acc={after['accuracy']}")
    print(after["report"])

    out_dir = Path(f"models_finetuned/sentiment_{model_key}")
    out_dir.mkdir(parents=True, exist_ok=True)
    base_model.save_pretrained(out_dir)
    tokenizer.save_pretrained(out_dir)
    print(f"Модель сохранена → {out_dir}")

    row = {
        "model_key": model_key,
        "model_id": model_id,
        "n_train": len(train_df),
        "n_test": len(test_df),
        "epochs": epochs,
        "f1_before": before["f1_weighted"],
        "f1_after": after["f1_weighted"],
        "f1_delta": round(after["f1_weighted"] - before["f1_weighted"], 4),
        "acc_before": before["accuracy"],
        "acc_after": after["accuracy"],
        "train_sec": round(train_sec, 1),
    }
    RESULTS_CSV.parent.mkdir(exist_ok=True)
    if RESULTS_CSV.exists():
        existing = pd.read_csv(RESULTS_CSV)
        existing = existing[~((existing["model_key"] == model_key) &
                              (existing["n_train"] == row["n_train"]))]
        out = pd.concat([existing, pd.DataFrame([row])], ignore_index=True)
    else:
        out = pd.DataFrame([row])
    out.to_csv(RESULTS_CSV, index=False)
    print(f"\n→ {RESULTS_CSV}")
    print(f"ИТОГ {model_key}: F1 {row['f1_before']} → {row['f1_after']} "
          f"(Δ {row['f1_delta']:+.4f})")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:]]
    key = next((a for a in args if not a.isdigit()), "rubert_tiny")
    nums = [int(a) for a in args if a.isdigit()]
    n_train = nums[0] if nums else 2000
    n_epochs = nums[1] if len(nums) > 1 else 3
    main(key, n_train, n_epochs)
