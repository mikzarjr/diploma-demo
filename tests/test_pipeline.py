from src.pipeline import (
    assign_roles, score_call, analyze_transcript, format_report,
    CallAnalysis, OUTCOME_SCORE,
)
from src.benchmark_llm_tasks import CHECKLIST_KEYS

def test_assign_roles_passthrough_when_labeled():
    turns = [{"turn_id": 0, "speaker": "manager", "text": "привет"},
             {"turn_id": 1, "speaker": "client", "text": "да"}]
    assert assign_roles(turns) == turns

def test_assign_roles_heuristic_raw_labels():
    turns = [{"turn_id": 0, "speaker": "spk_0", "text": "здравствуйте"},
             {"turn_id": 1, "speaker": "spk_1", "text": "слушаю"},
             {"turn_id": 2, "speaker": "spk_0", "text": "предлагаю"}]
    roles = [t["speaker"] for t in assign_roles(turns)]
    assert roles == ["manager", "client", "manager"]

def _checklist(passed):
    return {k: (i < passed) for i, k in enumerate(CHECKLIST_KEYS)}

def test_score_call_all_passed_deal_won():
    cs, q, grade = score_call(_checklist(7), "deal_won")
    assert cs == 100.0
    assert q == 100.0
    assert grade == "A"

def test_score_call_all_failed_deal_lost():
    cs, q, grade = score_call(_checklist(0), "deal_lost")
    assert cs == 0.0
    assert q == 2.0
    assert grade == "D"

def test_score_call_grade_bands():
    cs, q, grade = score_call(_checklist(5), "follow_up_scheduled")
    assert grade in ("B", "C")
    assert 0 <= q <= 100

def test_score_call_unknown_outcome_defaults():
    _, q1, _ = score_call(_checklist(7), "что-то_странное")
    _, q2, _ = score_call(_checklist(7), "no_decision")
    assert q1 == q2

def test_outcome_score_table_complete():
    for outcome in ["deal_won", "deal_lost", "follow_up_scheduled",
                    "no_decision", "unreachable"]:
        assert outcome in OUTCOME_SCORE

SAMPLE_TURNS = [
    {"turn_id": 0, "speaker": "manager", "text": "Здравствуйте, это Олег."},
    {"turn_id": 1, "speaker": "client", "text": "Да, слушаю вас."},
    {"turn_id": 2, "speaker": "manager", "text": "Удобно обсудить?"},
    {"turn_id": 3, "speaker": "client", "text": "Давайте, хорошо."},
]

def _fake_sentiment(text: str) -> str:
    return "neutral"

def test_analyze_transcript_returns_call_analysis():
    a = analyze_transcript(SAMPLE_TURNS, call_id="t1",
                           llm_model="mock", sentiment_fn=_fake_sentiment)
    assert isinstance(a, CallAnalysis)
    assert a.call_id == "t1"

def test_analyze_transcript_structure():
    a = analyze_transcript(SAMPLE_TURNS, call_id="t1",
                           llm_model="mock", sentiment_fn=_fake_sentiment)
    assert set(a.checklist.keys()) == set(CHECKLIST_KEYS)
    assert 0.0 <= a.checklist_score <= 100.0
    assert 0.0 <= a.quality_score <= 100.0
    assert a.grade in ("A", "B", "C", "D")

def test_analyze_transcript_sentiment_on_client_only():
    a = analyze_transcript(SAMPLE_TURNS, call_id="t1",
                           llm_model="mock", sentiment_fn=_fake_sentiment)
    for turn in a.transcript:
        if turn.speaker == "client":
            assert turn.sentiment == "neutral"
        else:
            assert turn.sentiment is None

def test_analyze_transcript_meta_has_timings():
    a = analyze_transcript(SAMPLE_TURNS, call_id="t1",
                           llm_model="mock", sentiment_fn=_fake_sentiment)
    assert "total_sec" in a.meta
    assert "llm_model" in a.meta and a.meta["llm_model"] == "mock"

def test_to_dict_serializable():
    import json
    a = analyze_transcript(SAMPLE_TURNS, call_id="t1",
                           llm_model="mock", sentiment_fn=_fake_sentiment)
    json.dumps(a.to_dict(), ensure_ascii=False)

def test_format_report_contains_key_sections():
    a = analyze_transcript(SAMPLE_TURNS, call_id="t1",
                           llm_model="mock", sentiment_fn=_fake_sentiment)
    report = format_report(a)
    assert "Анализ звонка t1" in report
    assert "Чек-лист" in report
    assert "Оценка качества" in report
