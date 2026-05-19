import math

from src.metrics import (
    normalize_text, tokenize, normalize_for_fact,
    cohen_kappa, per_class_f1, macro_f1_binary,
    lcs_length, rouge_l, rouge_n,
    fact_match, fact_metrics,
    mcnemar_exact, pearson,
    bootstrap_wer_ci, extract_json,
)

def test_normalize_text_basic():
    assert normalize_text("Ёлка, ПРИВЕТ!") == "елка привет"

def test_normalize_text_collapses_spaces():
    assert normalize_text("  много   пробелов  ") == "много пробелов"

def test_normalize_text_empty():
    assert normalize_text("") == ""
    assert normalize_text(None) == ""

def test_tokenize():
    assert tokenize("Кот, сидит! на 5 столе") == ["кот", "сидит", "на", "5", "столе"]

def test_normalize_for_fact_drops_short():
    assert normalize_for_fact("я не в логистике") == {"логистике"}

def test_cohen_kappa_perfect_agreement():
    assert cohen_kappa([1, 1, 0, 0], [1, 1, 0, 0]) == 1.0

def test_cohen_kappa_perfect_disagreement():
    assert math.isclose(cohen_kappa([1, 0, 1, 0], [0, 1, 0, 1]), -1.0)

def test_cohen_kappa_empty():
    assert cohen_kappa([], []) == 0.0

def test_cohen_kappa_range():
    k = cohen_kappa([1, 1, 1, 0, 0], [1, 0, 1, 0, 1])
    assert -1.0 <= k <= 1.0

def test_per_class_f1_known():
    m = per_class_f1([1, 1, 0, 0], [1, 0, 0, 0], positive=1)
    assert m["tp"] == 1 and m["fp"] == 0 and m["fn"] == 1
    assert math.isclose(m["precision"], 1.0)
    assert math.isclose(m["recall"], 0.5)
    assert math.isclose(m["f1"], 2 / 3)

def test_macro_f1_perfect():
    assert macro_f1_binary([1, 0, 1, 0], [1, 0, 1, 0]) == 1.0

def test_lcs_length():
    assert lcs_length(["a", "b", "c", "d"], ["a", "c", "d"]) == 3
    assert lcs_length([], ["a"]) == 0

def test_rouge_l_identical():
    assert rouge_l("кот сидит на столе", "кот сидит на столе") == 1.0

def test_rouge_l_disjoint():
    assert rouge_l("кот сидит", "совсем другое") == 0.0

def test_rouge_l_empty():
    assert rouge_l("", "что-то") == 0.0

def test_rouge_n_identical():
    assert rouge_n("один два три", "один два три", 1) == 1.0
    assert rouge_n("один два три", "один два три", 2) == 1.0

def test_rouge_n_too_short():
    assert rouge_n("один", "один", 2) == 0.0

def test_fact_match_positive():
    assert fact_match("клиент работает логистике",
                      ["клиент сидит логистике"]) is True

def test_fact_match_negative():
    assert fact_match("бюджет десять тысяч рублей",
                      ["совсем другое предложение"]) is False

def test_fact_match_empty():
    assert fact_match("", ["что-то"]) is False

def test_fact_metrics_perfect():
    facts = ["клиент работает логистике", "бюджет десять тысяч"]
    m = fact_metrics(facts, facts)
    assert math.isclose(m["fact_recall"], 1.0)
    assert math.isclose(m["fact_precision"], 1.0)
    assert math.isclose(m["fact_f1"], 1.0)

def test_fact_metrics_empty_gold():
    m = fact_metrics([], ["что-то"])
    assert m["fact_f1"] == 0.0

def test_mcnemar_no_discordant():
    assert mcnemar_exact(0, 0) == 1.0

def test_mcnemar_symmetric():
    assert mcnemar_exact(10, 10) > 0.9

def test_mcnemar_extreme():
    assert mcnemar_exact(20, 1) < 0.05

def test_mcnemar_range():
    for b, c in [(5, 3), (0, 7), (15, 12)]:
        assert 0.0 <= mcnemar_exact(b, c) <= 1.0

def test_pearson_perfect_positive():
    assert math.isclose(pearson([1, 2, 3, 4], [2, 4, 6, 8]), 1.0)

def test_pearson_perfect_negative():
    assert math.isclose(pearson([1, 2, 3, 4], [4, 3, 2, 1]), -1.0)

def test_pearson_too_few():
    assert pearson([1], [2]) == 0.0

def test_bootstrap_wer_ci_perfect():
    refs = ["кот сидит на столе", "окно открыто"]
    point, lo, hi = bootstrap_wer_ci(refs, refs, n_iter=100)
    assert point == 0.0
    assert lo == 0.0 and hi == 0.0

def test_bootstrap_wer_ci_bounds():
    refs = ["кот сидит на столе", "окно широко открыто"]
    hyps = ["кот сел на столе", "окно открыто"]
    point, lo, hi = bootstrap_wer_ci(refs, hyps, n_iter=300, seed=1)
    assert lo <= point <= hi
    assert 0.0 <= point <= 1.0

def test_bootstrap_wer_ci_empty():
    point, lo, hi = bootstrap_wer_ci([], [], n_iter=10)
    assert math.isnan(point)

def test_extract_json_plain():
    assert extract_json('{"a": 1, "b": 2}') == {"a": 1, "b": 2}

def test_extract_json_surrounded_by_text():
    assert extract_json('Вот ответ: {"x": 10} — готово') == {"x": 10}

def test_extract_json_fenced():
    assert extract_json('```json\n{"y": 5}\n```') == {"y": 5}

def test_extract_json_invalid():
    assert extract_json("совсем не json") is None
    assert extract_json("") is None

def test_extract_json_nested():
    obj = extract_json('{"checklist": {"greeting": true}, "facts": [1, 2]}')
    assert obj["checklist"]["greeting"] is True
    assert obj["facts"] == [1, 2]
