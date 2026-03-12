"""Test Expert Agent confidence-driven state logic."""
from agents.expert import classify_field, FieldStatus, determine_next_question


def test_classify_field_empty_when_none():
    assert classify_field(None, None) == FieldStatus.EMPTY


def test_classify_field_empty_when_low_confidence():
    assert classify_field("some value", 0.3) == FieldStatus.EMPTY


def test_classify_field_uncertain_when_mid_confidence():
    assert classify_field("some value", 0.6) == FieldStatus.UNCERTAIN


def test_classify_field_confirmed_when_high_confidence():
    assert classify_field("some value", 0.9) == FieldStatus.CONFIRMED


def test_classify_field_confirmed_when_user_provided():
    """User-provided values (confidence=None) are always confirmed."""
    assert classify_field("7.2 mmol", None) == FieldStatus.CONFIRMED


def test_determine_next_question_asks_glucose_first():
    collected = {"glucose": None, "diet": None, "medication": None}
    field, status = determine_next_question(collected)
    assert field == "glucose"
    assert status == FieldStatus.EMPTY


def test_determine_next_question_skips_confirmed():
    collected = {
        "glucose": {"value": "7.2", "confidence": 0.9},
        "diet": {"value": "Chicken Rice", "confidence": 0.85},
        "medication": None,
    }
    field, status = determine_next_question(collected)
    assert field == "medication"
    assert status == FieldStatus.EMPTY


def test_determine_next_question_confirms_uncertain():
    collected = {
        "glucose": {"value": "7.2", "confidence": 0.9},
        "diet": {"value": "Chicken Rice", "confidence": 0.6},
        "medication": None,
    }
    field, status = determine_next_question(collected)
    assert field == "diet"
    assert status == FieldStatus.UNCERTAIN


def test_determine_next_question_all_confirmed():
    collected = {
        "glucose": {"value": "7.2", "confidence": 0.9},
        "diet": {"value": "Chicken Rice", "confidence": 0.85},
        "medication": {"value": "Metformin 500mg", "confidence": 0.9},
    }
    field, status = determine_next_question(collected)
    assert field is None
    assert status is None
