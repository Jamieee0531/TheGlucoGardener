"""
意图路由回归测试（更新至两级架构）
覆盖四类场景：
  A. 明确 companion（无医疗词汇）
  B. 易误判 → companion（有医疗词汇但本质是情绪倾诉）← 核心回归
  C. 明确 medical（提问 / 求助 / 症状报告）
  D. 带负面情绪的症状陈述 → 必须保持 medical（安全关键）
"""
import json
import pytest
from unittest.mock import MagicMock, patch

from chatbot.agents.triage import triage_node, _COMPANION_UTTERANCES


# ── 辅助 ──────────────────────────────────────────────────────────────

def _make_l1_router(name):
    result = MagicMock()
    result.name = name
    router = MagicMock()
    router.return_value = result
    return router


def _make_l2_router(name):
    result = MagicMock()
    result.name = name
    router = MagicMock()
    router.return_value = result
    return router


def _state(user_input, emotion="neutral", history=None, vision_result=None):
    return {
        "user_input":    user_input,
        "emotion_label": emotion,
        "user_id":       "test_user",
        "history":       history or [],
        "glucose_readings": [],
        "vision_result": vision_result or [],
        "sub_intent":    None,
    }


def _l1_json(intent, reasoning="test"):
    return json.dumps({"reasoning": reasoning, "intents": [intent]})


def _l2_json(sub):
    return json.dumps({"sub_intent": sub})


# ── A. 明确 companion ─────────────────────────────────────────────────

CLEAR_COMPANION_CASES = [
    "今天心情不好", "好累啊", "你好", "谢谢你", "觉得孤独",
    "家人不理解我", "I'm feeling a bit down", "just want to talk",
    "good morning", "I feel lonely",
]

@patch("chatbot.agents.triage.get_health_store")
@patch("chatbot.agents.triage._get_router")
@pytest.mark.parametrize("text", CLEAR_COMPANION_CASES)
def test_clear_companion_via_sr(mock_router, mock_store, text):
    mock_router.return_value = _make_l1_router("companion")
    mock_store.return_value  = MagicMock()
    result = triage_node(_state(text))
    assert result["intent"] == "companion", f"期望 companion：{text!r}"
    assert result["sub_intent"] is None


# ── B. 易误判 → companion（有医疗词汇但本质情绪倾诉）────────────────

EMOTIONAL_HEALTH_CASES = [
    ("我糖尿病好焦虑",                    "fearful"),
    ("每天保持健康习惯好累",              "sad"),
    ("得了糖尿病真的好害怕",              "fearful"),
    ("控制血糖真的好累",                  "sad"),
    ("每天吃药好烦",                      "angry"),
    ("生病了好难受",                      "sad"),
    ("I'm so stressed about my diabetes", "fearful"),
    ("managing my health is exhausting",  "sad"),
    ("being diabetic is so tiring",       "sad"),
    ("living with diabetes is really hard","sad"),
]

@patch("chatbot.agents.triage.get_health_store")
@patch("chatbot.agents.triage._get_router")
@pytest.mark.parametrize("text,emotion", EMOTIONAL_HEALTH_CASES)
def test_emotional_health_stays_companion_via_sr(mock_router, mock_store, text, emotion):
    """SR 判为 companion，triage_node 应直接透传，不受情绪影响。"""
    mock_router.return_value = _make_l1_router("companion")
    mock_store.return_value  = MagicMock()
    result = triage_node(_state(text, emotion=emotion))
    assert result["intent"] == "companion", f"应为 companion：{text!r}"


@patch("chatbot.agents.triage.get_health_store")
@patch("chatbot.agents.triage.call_sealion")
@patch("chatbot.agents.triage._get_router")
@pytest.mark.parametrize("text,emotion", EMOTIONAL_HEALTH_CASES)
def test_emotional_health_stays_companion_via_llm(mock_router, mock_llm, mock_store, text, emotion):
    """SR 置信度不足时 LLM CoT 也应判为 companion。"""
    mock_router.return_value = _make_l1_router(None)
    mock_llm.return_value    = _l1_json("companion", "用户在情绪倾诉")
    mock_store.return_value  = MagicMock()
    result = triage_node(_state(text, emotion=emotion))
    assert result["intent"] == "companion", f"LLM 路径应为 companion：{text!r}"


# ── C. 明确 medical ────────────────────────────────────────────────────

CLEAR_MEDICAL_CASES = [
    "我血糖最近偏高怎么办", "吃了二甲双胍头晕正常吗", "血糖8.9是高吗",
    "胰岛素怎么打", "HbA1c多少正常", "这个药有什么副作用",
    "my blood sugar is high what should I do", "side effects of metformin",
    "glucose reading 9.5 is it normal", "can I exercise with low blood sugar",
]

@patch("chatbot.agents.triage.get_health_store")
@patch("chatbot.agents.triage._prefetch_rag")
@patch("chatbot.agents.triage._get_sub_router")
@patch("chatbot.agents.triage._get_router")
@pytest.mark.parametrize("text", CLEAR_MEDICAL_CASES)
def test_clear_medical_via_sr(mock_router, mock_sub, mock_rag, mock_store, text):
    mock_router.return_value = _make_l1_router("medical")
    mock_sub.return_value    = _make_l2_router("general_medical")
    mock_store.return_value  = MagicMock()
    result = triage_node(_state(text, emotion="neutral"))
    assert result["intent"] == "medical", f"期望 medical：{text!r}"
    assert result["sub_intent"] is not None


@patch("chatbot.agents.triage.get_health_store")
@patch("chatbot.agents.triage._prefetch_rag")
@patch("chatbot.agents.triage._get_sub_router")
@patch("chatbot.agents.triage.call_sealion")
@patch("chatbot.agents.triage._get_router")
@pytest.mark.parametrize("text", CLEAR_MEDICAL_CASES)
def test_clear_medical_via_llm(mock_router, mock_llm, mock_sub, mock_rag, mock_store, text):
    mock_router.return_value = _make_l1_router(None)
    mock_llm.return_value    = _l1_json("medical", "用户在提问")
    mock_sub.return_value    = _make_l2_router("general_medical")
    mock_store.return_value  = MagicMock()
    result = triage_node(_state(text, emotion="neutral"))
    assert result["intent"] == "medical", f"LLM 路径应为 medical：{text!r}"


# ── D. 安全关键：负面情绪 + 症状 → 必须为 medical（不被覆盖为 companion）─

FEARFUL_SYMPTOM_CASES = [
    ("我头很晕，手在抖",         "fearful"),
    ("打完胰岛素感觉不对劲",     "fearful"),
    ("我最近血糖一直很高",       "sad"),
    ("feeling shaky and sweaty", "fearful"),
]

@patch("chatbot.agents.triage.get_health_store")
@patch("chatbot.agents.triage._prefetch_rag")
@patch("chatbot.agents.triage._get_sub_router")
@patch("chatbot.agents.triage._get_router")
@pytest.mark.parametrize("text,emotion", FEARFUL_SYMPTOM_CASES)
def test_fearful_symptom_becomes_hybrid(mock_router, mock_sub, mock_rag, mock_store, text, emotion):
    """SR 判为 medical + 负面情绪 → 升级为 hybrid（而非丢弃医疗内容）。"""
    mock_router.return_value = _make_l1_router("medical")
    mock_sub.return_value    = _make_l2_router("complication_query")
    mock_store.return_value  = MagicMock()
    result = triage_node(_state(text, emotion=emotion))
    assert result["intent"] in ("medical", "hybrid"), \
        f"负面情绪+症状应为 medical 或 hybrid：{text!r}"


# ── E. companion utterances 覆盖验证 ─────────────────────────────────

NEW_COMPANION_UTTERANCES = [
    "我糖尿病好焦虑", "得了糖尿病真的好害怕", "每天保持健康习惯好累",
    "控制血糖真的好累", "每天吃药好烦", "生病了好难受",
    "I'm so stressed about my diabetes", "managing my health is exhausting",
    "being diabetic is so tiring", "I hate having to watch what I eat",
    "living with diabetes is really hard", "I feel overwhelmed by my condition",
]

@pytest.mark.parametrize("utterance", NEW_COMPANION_UTTERANCES)
def test_companion_utterances_in_list(utterance):
    assert utterance in _COMPANION_UTTERANCES, f"utterance 未在列表中：{utterance!r}"


# ── F. 降级与容错 ──────────────────────────────────────────────────────

@patch("chatbot.agents.triage.get_health_store")
@patch("chatbot.agents.triage.call_sealion")
@patch("chatbot.agents.triage._get_router")
def test_llm_invalid_json_falls_back_to_companion(mock_router, mock_llm, mock_store):
    mock_router.return_value = _make_l1_router(None)
    mock_llm.return_value    = "not json at all"
    mock_store.return_value  = MagicMock()
    result = triage_node(_state("随便一句话"))
    assert result["intent"] == "companion"


@patch("chatbot.agents.triage.get_health_store")
@patch("chatbot.agents.triage.call_sealion")
@patch("chatbot.agents.triage._get_router")
def test_llm_unknown_intent_falls_back_to_companion(mock_router, mock_llm, mock_store):
    mock_router.return_value = _make_l1_router(None)
    mock_llm.return_value    = json.dumps({"reasoning": "test", "intents": ["unknown_label"]})
    mock_store.return_value  = MagicMock()
    result = triage_node(_state("随便一句话"))
    assert result["intent"] == "companion"


# ── G. 历史上下文注入验证 ─────────────────────────────────────────────

@patch("chatbot.agents.triage.get_health_store")
@patch("chatbot.agents.triage.call_sealion")
@patch("chatbot.agents.triage._get_router")
def test_recent_history_injected_into_llm(mock_router, mock_llm, mock_store):
    mock_router.return_value = _make_l1_router(None)
    mock_llm.return_value    = _l1_json("companion")
    mock_store.return_value  = MagicMock()

    history = [
        {"role": "user",      "content": "我最近很累"},
        {"role": "assistant", "content": "怎么了？"},
    ]
    triage_node(_state("就是身体不舒服", history=history))

    user_message = mock_llm.call_args[0][1]
    assert "我最近很累" in user_message, "历史应注入 LLM"


@patch("chatbot.agents.triage.get_health_store")
@patch("chatbot.agents.triage.call_sealion")
@patch("chatbot.agents.triage._get_router")
def test_emotion_hint_injected_when_not_neutral(mock_router, mock_llm, mock_store):
    mock_router.return_value = _make_l1_router(None)
    mock_llm.return_value    = _l1_json("companion")
    mock_store.return_value  = MagicMock()
    triage_node(_state("我糖尿病好焦虑", emotion="fearful"))
    assert "fearful" in mock_llm.call_args[0][1]


@patch("chatbot.agents.triage.get_health_store")
@patch("chatbot.agents.triage.call_sealion")
@patch("chatbot.agents.triage._get_router")
def test_emotion_hint_skipped_when_neutral(mock_router, mock_llm, mock_store):
    mock_router.return_value = _make_l1_router(None)
    mock_llm.return_value    = _l1_json("companion")
    mock_store.return_value  = MagicMock()
    triage_node(_state("你好", emotion="neutral"))
    assert "MERaLiON" not in mock_llm.call_args[0][1]
