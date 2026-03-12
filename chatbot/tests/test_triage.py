"""Test triage keyword pre-classification."""
from agents.triage import keyword_preclassify, _simple_emotion_detect


def test_medical_keywords():
    assert keyword_preclassify("我血糖有点高") == "medical"
    assert keyword_preclassify("吃了药") == "medical"


def test_alert_keywords():
    assert keyword_preclassify("我头好晕快晕倒了") == "alert"


def test_emotional_keywords():
    assert keyword_preclassify("我好难过") == "emotional"
    assert keyword_preclassify("最近压力好大") == "emotional"


def test_task_keywords():
    assert keyword_preclassify("帮我打卡") == "task"


def test_ambiguous_returns_none():
    """Ambiguous input should return None (fall back to LLM)."""
    assert keyword_preclassify("今天天气不错") is None
    assert keyword_preclassify("你好") is None


def test_simple_emotion_detects_sad():
    assert _simple_emotion_detect("我好难过", "neutral", 0.0, "text") == "sad"


def test_simple_emotion_detects_anxious():
    assert _simple_emotion_detect("我很担心", "neutral", 0.0, "text") == "anxious"


def test_simple_emotion_defaults_neutral():
    assert _simple_emotion_detect("今天天气不错", "neutral", 0.0, "text") == "neutral"


def test_simple_emotion_uses_voice_when_confident():
    """When voice mode and confidence > 0.6, use voice emotion."""
    assert _simple_emotion_detect("text doesn't matter", "sad", 0.8, "voice") == "sad"
