from transformers import pipeline as hf_pipeline

_LABEL_MAP = {
    "POSITIVE": "positive", "NEUTRAL": "neutral", "NEGATIVE": "negative",
    "positive": "positive", "neutral": "neutral", "negative": "negative",
    "Positive": "positive", "Neutral": "neutral", "Negative": "negative",
    "LABEL_0": "negative", "LABEL_1": "neutral", "LABEL_2": "positive",
}


def _make_runner(model_name: str):
    _pipe = None

    def predict(text: str) -> str:
        nonlocal _pipe
        if _pipe is None:
            _pipe = hf_pipeline(
                "text-classification",
                model=model_name,
                tokenizer=model_name,
                truncation=True,
                max_length=512,
                device=-1,
            )
        raw_label = _pipe(text)[0]["label"]
        return _LABEL_MAP.get(raw_label, raw_label.lower())

    predict.__name__ = model_name
    return predict


transcribe_sentiment_rubert_tiny = _make_runner("seara/rubert-tiny2-russian-sentiment")
transcribe_sentiment_rubert_base = _make_runner("tabularisai/multilingual-sentiment-analysis")
transcribe_sentiment_xlm = _make_runner("cardiffnlp/twitter-xlm-roberta-base-sentiment-multilingual")
