"""Test triage keyword pre-classification and emotion resolution."""
from agents.triage import keyword_preclassify, resolve_emotion


def test_medical_keywords():
    assert keyword_preclassify("我血糖有点高") == "medical"
    assert keyword_preclassify("吃了药") == "medical"


def test_emotional_keywords():
    assert keyword_preclassify("我好难过") == "emotional"
    assert keyword_preclassify("最近压力好大") == "emotional"


def test_ambiguous_returns_none():
    """Ambiguous input should return None (fall back to LLM)."""
    assert keyword_preclassify("今天天气不错") is None
    assert keyword_preclassify("你好") is None


def test_emotion_voice_confident_uses_meralion():
    """Voice + confidence >= 0.6 should use MERaLiON result."""
    assert resolve_emotion("sad", 0.8, "voice") == "sad"
    assert resolve_emotion("anxious", 0.6, "voice") == "anxious"


def test_emotion_voice_low_confidence_neutral():
    """Voice + confidence < 0.6 should be neutral."""
    assert resolve_emotion("sad", 0.5, "voice") == "neutral"
    assert resolve_emotion("angry", 0.3, "voice") == "neutral"


def test_emotion_text_always_neutral():
    """Text input should always be neutral regardless of content."""
    assert resolve_emotion("neutral", 0.0, "text") == "neutral"
    assert resolve_emotion("sad", 0.9, "text") == "neutral"
