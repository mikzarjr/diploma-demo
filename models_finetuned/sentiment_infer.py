from __future__ import annotations

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification


class SentimentModel:
    def __init__(self, model_dir: str = "sentiment_rubert_tiny"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_dir)
        self.model.eval()
        self.id2label = self.model.config.id2label

    def predict(self, text: str) -> str:
        return self.predict_batch([text])[0]

    def predict_batch(self, texts: list[str]) -> list[str]:
        if not texts:
            return []
        enc = self.tokenizer(texts, padding=True, truncation=True,
                             max_length=128, return_tensors="pt")
        with torch.no_grad():
            logits = self.model(**enc).logits
        return [self.id2label[int(i)] for i in logits.argmax(-1)]


if __name__ == "__main__":
    model = SentimentModel("sentiment_rubert_tiny")
    samples = [
        "Спасибо, всё отлично, оформляем договор!",
        "Это слишком дорого, мне не подходит.",
        "Хорошо, я подумаю и перезвоню.",
    ]
    for text in samples:
        print(f"{model.predict(text):9} ← {text}")
