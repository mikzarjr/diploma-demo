from __future__ import annotations

import json
import random
import re
from math import comb
from typing import Optional

from jiwer import wer as _jiwer_wer

_PUNCT_RE = re.compile(r"[^а-яa-z0-9\s]")
_WS_RE = re.compile(r"\s+")
_TOKEN_RE = re.compile(r"[а-яa-z0-9]+")

def normalize_text(text: str) -> str:
    text = (text or "").lower().replace("ё", "е")
    text = _PUNCT_RE.sub(" ", text)
    return _WS_RE.sub(" ", text).strip()

def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall((text or "").lower().replace("ё", "е"))

def normalize_for_fact(text: str) -> set[str]:
    return {t for t in tokenize(text) if len(t) > 2}

def bootstrap_wer_ci(references: list[str], hypotheses: list[str],
                     n_iter: int = 1000, seed: int = 42,
                     alpha: float = 0.05) -> tuple[float, float, float]:
    n = len(references)
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    point = _jiwer_wer(" ".join(references), " ".join(hypotheses))
    rng = random.Random(seed)
    samples = []
    for _ in range(n_iter):
        idx = [rng.randrange(n) for _ in range(n)]
        ref = " ".join(references[i] for i in idx)
        hyp = " ".join(hypotheses[i] for i in idx)
        samples.append(_jiwer_wer(ref, hyp))
    samples.sort()
    lo = samples[int(n_iter * (alpha / 2))]
    hi = samples[int(n_iter * (1 - alpha / 2)) - 1]
    return point, lo, hi

def cohen_kappa(y_true: list[int], y_pred: list[int]) -> float:
    if not y_true:
        return 0.0
    n = len(y_true)
    p_o = sum(1 for a, b in zip(y_true, y_pred) if a == b) / n
    p_true = sum(y_true) / n
    p_pred = sum(y_pred) / n
    p_e = p_true * p_pred + (1 - p_true) * (1 - p_pred)
    if p_e == 1.0:
        return 1.0 if p_o == 1.0 else 0.0
    return (p_o - p_e) / (1 - p_e)

def per_class_f1(y_true: list[int], y_pred: list[int], positive: int = 1) -> dict:
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == positive and p == positive)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t != positive and p == positive)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == positive and p != positive)
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return {"precision": prec, "recall": rec, "f1": f1, "tp": tp, "fp": fp, "fn": fn}

def macro_f1_binary(y_true: list[int], y_pred: list[int]) -> float:
    pos = per_class_f1(y_true, y_pred, positive=1)["f1"]
    neg = per_class_f1(y_true, y_pred, positive=0)["f1"]
    return (pos + neg) / 2

def lcs_length(a: list[str], b: list[str]) -> int:
    m, n = len(a), len(b)
    if not m or not n:
        return 0
    prev = [0] * (n + 1)
    for i in range(m):
        cur = [0] * (n + 1)
        for j in range(n):
            cur[j + 1] = prev[j] + 1 if a[i] == b[j] else max(cur[j], prev[j + 1])
        prev = cur
    return prev[n]

def rouge_l(reference: str, hypothesis: str) -> float:
    ref, hyp = tokenize(reference), tokenize(hypothesis)
    if not ref or not hyp:
        return 0.0
    lcs = lcs_length(ref, hyp)
    p = lcs / len(hyp)
    r = lcs / len(ref)
    return 2 * p * r / (p + r) if (p + r) else 0.0

def rouge_n(reference: str, hypothesis: str, n: int) -> float:
    from collections import Counter
    ref, hyp = tokenize(reference), tokenize(hypothesis)
    if len(ref) < n or len(hyp) < n:
        return 0.0
    ref_ng = Counter(tuple(ref[i:i + n]) for i in range(len(ref) - n + 1))
    hyp_ng = Counter(tuple(hyp[i:i + n]) for i in range(len(hyp) - n + 1))
    overlap = sum((ref_ng & hyp_ng).values())
    p = overlap / max(sum(hyp_ng.values()), 1)
    r = overlap / max(sum(ref_ng.values()), 1)
    return 2 * p * r / (p + r) if (p + r) else 0.0

def fact_match(gold_fact: str, hyp_facts: list[str],
               jaccard_threshold: float = 0.45) -> bool:
    gold = normalize_for_fact(gold_fact)
    if not gold:
        return False
    for h in hyp_facts:
        hs = normalize_for_fact(h)
        if not hs:
            continue
        union = len(gold | hs)
        if union and len(gold & hs) / union >= jaccard_threshold:
            return True
    return False

def fact_metrics(gold: list[str], hyp: list[str]) -> dict:
    if not gold:
        return {"fact_precision": 0.0, "fact_recall": 0.0, "fact_f1": 0.0}
    matched_gold = [g for g in gold if fact_match(g, hyp)]
    matched_hyp = [h for h in hyp if fact_match(h, gold)]
    recall = len(matched_gold) / len(gold)
    precision = (len(matched_hyp) / len(hyp)) if hyp else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"fact_precision": precision, "fact_recall": recall, "fact_f1": f1}

def mcnemar_exact(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    return min(1.0, 2 * tail)

def pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs) ** 0.5
    vy = sum((y - my) ** 2 for y in ys) ** 0.5
    return cov / (vx * vy) if vx and vy else 0.0

_JSON_BLOCK_RE = re.compile(r"\{[\s\S]*\}", re.MULTILINE)
_FENCED_RE = re.compile(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```")

def extract_json(text: str) -> Optional[dict]:
    if not text:
        return None
    candidates = [text.strip()]
    m = _JSON_BLOCK_RE.search(text)
    if m:
        candidates.insert(0, m.group(0))
    for c in candidates:
        try:
            obj = json.loads(c)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass
    fenced = _FENCED_RE.search(text)
    if fenced:
        try:
            obj = json.loads(fenced.group(1))
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None
    return None
