"""
两级意图路由综合测试集
覆盖：
  1. L1 路由（crisis / medical / companion）
  2. Hybrid 检测（medical + 强负面情绪）
  3. L2 sub_intent 精分类（6 类）
  4. 图片驱动的 sub_intent
  5. LLM CoT 兜底（L1 + L2）
  6. Multi-intent（LLM 返回 medical + companion）
  7. Crisis Agent（4 种语言）
  8. 边界情况：空输入、SR 异常、兜底链完整性
"""
import json
import pytest
from unittest.mock import MagicMock, patch

from chatbot.agents.triage import triage_node, _CRISIS_UTTERANCES, _MEDICAL_UTTERANCES
from chatbot.agents.crisis import crisis_agent_node
from chatbot.config.settings import (
    INTENT_CRISIS, INTENT_MEDICAL, INTENT_COMPANION, INTENT_HYBRID,
    SUB_INTENT_GLUCOSE, SUB_INTENT_FOOD, SUB_INTENT_MEDICATION,
    SUB_INTENT_EXERCISE, SUB_INTENT_COMPLICATION, SUB_INTENT_GENERAL,
)


# ── 辅助 ──────────────────────────────────────────────────────────────

def _make_router(name):
    result = MagicMock()
    result.name = name
    router = MagicMock()
    router.return_value = result
    return router


def _state(user_input, emotion="neutral", vision_result=None, history=None):
    return {
        "user_input":       user_input,
        "emotion_label":    emotion,
        "user_id":          "test_user",
        "history":          history or [],
        "glucose_readings": [],
        "vision_result":    vision_result or [],
        "sub_intent":       None,
        "user_profile":     {"name": "测试用户", "language": "Chinese"},
    }


def _l1_json(*intents, reasoning="test"):
    return json.dumps({"reasoning": reasoning, "intents": list(intents)})


def _l2_json(sub):
    return json.dumps({"sub_intent": sub})


# ═══════════════════════════════════════════════════════════════════════
# 1. L1 路由：crisis
# ═══════════════════════════════════════════════════════════════════════

CRISIS_INPUTS = [
    ("我不想活了",         "zh"),
    ("想放弃治疗",         "zh"),
    ("不想再撑了",         "zh"),
    ("I want to give up",  "en"),
    ("want to end it",     "en"),
    ("tidak mahu hidup lagi", "ms"),
]

@patch("chatbot.agents.triage.get_health_store")
@patch("chatbot.agents.triage._get_router")
@pytest.mark.parametrize("text,lang", CRISIS_INPUTS)
def test_crisis_via_sr(mock_router, mock_store, text, lang):
    """SR 识别 crisis → 直接路由，不进 L2，sub_intent 为 None。"""
    mock_router.return_value = _make_router(INTENT_CRISIS)
    mock_store.return_value  = MagicMock()
    result = triage_node(_state(text))
    assert result["intent"]     == INTENT_CRISIS
    assert result["sub_intent"] is None


@patch("chatbot.agents.triage.get_health_store")
@patch("chatbot.agents.triage.call_sealion")
@patch("chatbot.agents.triage._get_router")
def test_crisis_via_llm_cot(mock_router, mock_llm, mock_store):
    """SR 置信度不足，LLM 返回 crisis → 触发 crisis 路由。"""
    mock_router.return_value = _make_router(None)
    mock_llm.return_value    = _l1_json(INTENT_CRISIS)
    mock_store.return_value  = MagicMock()
    result = triage_node(_state("真的撑不下去了"))
    assert result["intent"] == INTENT_CRISIS


@patch("chatbot.agents.triage.get_health_store")
@patch("chatbot.agents.triage._get_router")
def test_crisis_skips_l2(mock_router, mock_store):
    """crisis 不应进入 L2 sub_intent 分类。"""
    mock_router.return_value = _make_router(INTENT_CRISIS)
    mock_store.return_value  = MagicMock()
    with patch("chatbot.agents.triage._classify_sub_intent") as mock_l2:
        triage_node(_state("不想活了"))
        mock_l2.assert_not_called()


@pytest.mark.parametrize("text", [u for u, _ in CRISIS_INPUTS])
def test_crisis_utterances_in_list(text):
    assert text in _CRISIS_UTTERANCES, f"未在 crisis utterances 中：{text!r}"


# ═══════════════════════════════════════════════════════════════════════
# 2. Hybrid 检测（medical + 强负面情绪）
# ═══════════════════════════════════════════════════════════════════════

HYBRID_CASES = [
    ("我好害怕，血糖9.5正常吗", "fearful"),
    ("血糖一直高，真的好难受",   "sad"),
    ("药吃了还是这样，好烦",     "angry"),
]

@patch("chatbot.agents.triage.get_health_store")
@patch("chatbot.agents.triage._prefetch_rag")
@patch("chatbot.agents.triage._get_sub_router")
@patch("chatbot.agents.triage._get_router")
@pytest.mark.parametrize("text,emotion", HYBRID_CASES)
def test_medical_with_negative_emotion_becomes_hybrid(mock_router, mock_sub, mock_rag, mock_store, text, emotion):
    """SR 命中 medical + 负面情绪 → 升级为 hybrid。"""
    mock_router.return_value = _make_router(INTENT_MEDICAL)
    mock_sub.return_value    = _make_router(SUB_INTENT_GLUCOSE)
    mock_store.return_value  = MagicMock()
    result = triage_node(_state(text, emotion=emotion))
    assert result["intent"] == INTENT_HYBRID, f"应为 hybrid：{text!r}（情绪={emotion}）"
    assert result["sub_intent"] is not None


@patch("chatbot.agents.triage.get_health_store")
@patch("chatbot.agents.triage._prefetch_rag")
@patch("chatbot.agents.triage._get_sub_router")
@patch("chatbot.agents.triage._get_router")
def test_medical_with_neutral_emotion_stays_medical(mock_router, mock_sub, mock_rag, mock_store):
    """医疗问题 + neutral 情绪 → 保持 medical，不升级 hybrid。"""
    mock_router.return_value = _make_router(INTENT_MEDICAL)
    mock_sub.return_value    = _make_router(SUB_INTENT_GLUCOSE)
    mock_store.return_value  = MagicMock()
    result = triage_node(_state("血糖9.5正常吗", emotion="neutral"))
    assert result["intent"] == INTENT_MEDICAL


@patch("chatbot.agents.triage.get_health_store")
@patch("chatbot.agents.triage._prefetch_rag")
@patch("chatbot.agents.triage._get_sub_router")
@patch("chatbot.agents.triage._get_router")
def test_medical_with_happy_emotion_stays_medical(mock_router, mock_sub, mock_rag, mock_store):
    """医疗问题 + happy 情绪 → 保持 medical，不升级 hybrid。"""
    mock_router.return_value = _make_router(INTENT_MEDICAL)
    mock_sub.return_value    = _make_router(SUB_INTENT_FOOD)
    mock_store.return_value  = MagicMock()
    result = triage_node(_state("今天吃了鸡饭，心情不错，血糖会高吗", emotion="happy"))
    assert result["intent"] == INTENT_MEDICAL


@patch("chatbot.agents.triage.get_health_store")
@patch("chatbot.agents.triage._prefetch_rag")
@patch("chatbot.agents.triage._get_sub_router")
@patch("chatbot.agents.triage.call_sealion")
@patch("chatbot.agents.triage._get_router")
def test_llm_multi_intent_becomes_hybrid(mock_router, mock_llm, mock_sub, mock_rag, mock_store):
    """LLM CoT 返回 [medical, companion] → hybrid。"""
    mock_router.return_value = _make_router(None)
    mock_llm.return_value    = _l1_json(INTENT_MEDICAL, INTENT_COMPANION, reasoning="两者并存")
    mock_sub.return_value    = _make_router(SUB_INTENT_GLUCOSE)
    mock_store.return_value  = MagicMock()
    result = triage_node(_state("血糖高我很担心该怎么办"))
    assert result["intent"] == INTENT_HYBRID


# ═══════════════════════════════════════════════════════════════════════
# 3. L2 sub_intent 精分类
# ═══════════════════════════════════════════════════════════════════════

SUB_INTENT_CASES = [
    ("我血糖今天9.5正常吗",        SUB_INTENT_GLUCOSE),
    ("HbA1c多少正常",              SUB_INTENT_GLUCOSE),
    ("空腹血糖偏高",               SUB_INTENT_GLUCOSE),
    ("鸡饭GI值高吗",               SUB_INTENT_FOOD),
    ("糖尿病可以吃什么",           SUB_INTENT_FOOD),
    ("hawker food is it ok",       SUB_INTENT_FOOD),
    ("二甲双胍副作用",             SUB_INTENT_MEDICATION),
    ("胰岛素怎么打",               SUB_INTENT_MEDICATION),
    ("metformin side effects",     SUB_INTENT_MEDICATION),
    ("血糖高可以运动吗",           SUB_INTENT_EXERCISE),
    ("什么运动适合糖尿病",         SUB_INTENT_EXERCISE),
    ("can I exercise with diabetes",SUB_INTENT_EXERCISE),
    ("手脚麻木是怎么回事",         SUB_INTENT_COMPLICATION),
    ("伤口愈合慢",                 SUB_INTENT_COMPLICATION),
    ("足部护理怎么做",             SUB_INTENT_COMPLICATION),
]

@patch("chatbot.agents.triage.get_health_store")
@patch("chatbot.agents.triage._prefetch_rag")
@patch("chatbot.agents.triage._get_sub_router")
@patch("chatbot.agents.triage._get_router")
@pytest.mark.parametrize("text,expected_sub", SUB_INTENT_CASES)
def test_sub_intent_via_sr(mock_router, mock_sub, mock_rag, mock_store, text, expected_sub):
    """L1 命中 medical，L2 SR 返回正确 sub_intent。"""
    mock_router.return_value = _make_router(INTENT_MEDICAL)
    mock_sub.return_value    = _make_router(expected_sub)
    mock_store.return_value  = MagicMock()
    result = triage_node(_state(text, emotion="neutral"))
    assert result["sub_intent"] == expected_sub, f"期望 {expected_sub}：{text!r}"


@patch("chatbot.agents.triage.get_health_store")
@patch("chatbot.agents.triage._prefetch_rag")
@patch("chatbot.agents.triage.call_sealion")
@patch("chatbot.agents.triage._get_sub_router")
@patch("chatbot.agents.triage._get_router")
@pytest.mark.parametrize("text,expected_sub", SUB_INTENT_CASES[:6])
def test_sub_intent_via_llm_fallback(mock_router, mock_sub, mock_llm, mock_rag, mock_store, text, expected_sub):
    """L1 SR 命中 medical，L2 SR 置信度不足，LLM CoT 给出 sub_intent。"""
    mock_router.return_value = _make_router(INTENT_MEDICAL)
    mock_sub.return_value    = _make_router(None)      # L2 SR miss
    mock_llm.return_value    = _l2_json(expected_sub)  # L2 LLM hits
    mock_store.return_value  = MagicMock()
    result = triage_node(_state(text, emotion="neutral"))
    assert result["sub_intent"] == expected_sub, f"LLM L2 应给出 {expected_sub}：{text!r}"


@patch("chatbot.agents.triage.get_health_store")
@patch("chatbot.agents.triage._prefetch_rag")
@patch("chatbot.agents.triage.call_sealion")
@patch("chatbot.agents.triage._get_sub_router")
@patch("chatbot.agents.triage._get_router")
def test_sub_intent_llm_invalid_json_falls_to_general(mock_router, mock_sub, mock_llm, mock_rag, mock_store):
    """L2 LLM 返回无效 JSON → 兜底为 general_medical。"""
    mock_router.return_value = _make_router(INTENT_MEDICAL)
    mock_sub.return_value    = _make_router(None)
    mock_llm.return_value    = "bad json"
    mock_store.return_value  = MagicMock()
    result = triage_node(_state("随便一个医疗问题", emotion="neutral"))
    assert result["sub_intent"] == SUB_INTENT_GENERAL


# ═══════════════════════════════════════════════════════════════════════
# 4. 图片驱动的 sub_intent
# ═══════════════════════════════════════════════════════════════════════

@patch("chatbot.agents.triage.get_health_store")
@patch("chatbot.agents.triage._prefetch_rag")
@patch("chatbot.agents.triage._get_router")
def test_food_image_maps_to_food_inquiry(mock_router, mock_rag, mock_store):
    """FOOD 图片 → sub_intent = food_inquiry，不需要 SR/LLM。"""
    mock_router.return_value = _make_router(INTENT_MEDICAL)
    mock_store.return_value  = MagicMock()
    vision = [{"scene_type": "FOOD", "food_name": "鸡饭"}]
    result = triage_node(_state("我拍了一张食物照片", vision_result=vision))
    assert result["sub_intent"] == SUB_INTENT_FOOD


@patch("chatbot.agents.triage.get_health_store")
@patch("chatbot.agents.triage._prefetch_rag")
@patch("chatbot.agents.triage._get_router")
def test_medication_image_maps_to_medication_query(mock_router, mock_rag, mock_store):
    mock_router.return_value = _make_router(INTENT_MEDICAL)
    mock_store.return_value  = MagicMock()
    vision = [{"scene_type": "MEDICATION"}]
    result = triage_node(_state("我拍了一张药物照片", vision_result=vision))
    assert result["sub_intent"] == SUB_INTENT_MEDICATION


@patch("chatbot.agents.triage.get_health_store")
@patch("chatbot.agents.triage._prefetch_rag")
@patch("chatbot.agents.triage._get_router")
def test_report_image_maps_to_glucose_query(mock_router, mock_rag, mock_store):
    mock_router.return_value = _make_router(INTENT_MEDICAL)
    mock_store.return_value  = MagicMock()
    vision = [{"scene_type": "REPORT"}]
    result = triage_node(_state("我拍了一张化验单", vision_result=vision))
    assert result["sub_intent"] == SUB_INTENT_GLUCOSE


@patch("chatbot.agents.triage.get_health_store")
@patch("chatbot.agents.triage._prefetch_rag")
@patch("chatbot.agents.triage._get_sub_router")
@patch("chatbot.agents.triage._get_router")
def test_unknown_image_falls_to_sr(mock_router, mock_sub, mock_rag, mock_store):
    """UNKNOWN 图片不直接映射 sub_intent，继续走 L2 SR。"""
    mock_router.return_value = _make_router(INTENT_MEDICAL)
    mock_sub.return_value    = _make_router(SUB_INTENT_GENERAL)
    mock_store.return_value  = MagicMock()
    vision = [{"scene_type": "UNKNOWN"}]
    result = triage_node(_state("我发了一张照片", vision_result=vision))
    assert result["sub_intent"] == SUB_INTENT_GENERAL


# ═══════════════════════════════════════════════════════════════════════
# 5. LLM CoT 兜底链完整性（L1 miss → LLM → medical → L2）
# ═══════════════════════════════════════════════════════════════════════

@patch("chatbot.agents.triage.get_health_store")
@patch("chatbot.agents.triage._prefetch_rag")
@patch("chatbot.agents.triage._get_sub_router")
@patch("chatbot.agents.triage.call_sealion")
@patch("chatbot.agents.triage._get_router")
def test_full_llm_fallback_chain_medical(mock_router, mock_llm, mock_sub, mock_rag, mock_store):
    """L1 SR miss → LLM 返回 medical → L2 SR 命中 → sub_intent 正确。"""
    mock_router.return_value = _make_router(None)
    mock_llm.return_value    = _l1_json(INTENT_MEDICAL)
    mock_sub.return_value    = _make_router(SUB_INTENT_MEDICATION)
    mock_store.return_value  = MagicMock()
    result = triage_node(_state("这个药怎么吃", emotion="neutral"))
    assert result["intent"]    == INTENT_MEDICAL
    assert result["sub_intent"] == SUB_INTENT_MEDICATION


@patch("chatbot.agents.triage.get_health_store")
@patch("chatbot.agents.triage._prefetch_rag")
@patch("chatbot.agents.triage._get_sub_router")
@patch("chatbot.agents.triage.call_sealion")
@patch("chatbot.agents.triage._get_router")
def test_full_llm_fallback_chain_hybrid(mock_router, mock_llm, mock_sub, mock_rag, mock_store):
    """L1 SR miss → LLM 返回 [medical, companion] → hybrid + sub_intent。"""
    mock_router.return_value = _make_router(None)
    mock_llm.return_value    = _l1_json(INTENT_MEDICAL, INTENT_COMPANION)
    mock_sub.return_value    = _make_router(SUB_INTENT_EXERCISE)
    mock_store.return_value  = MagicMock()
    result = triage_node(_state("运动完血糖低我好担心啊"))
    assert result["intent"]    == INTENT_HYBRID
    assert result["sub_intent"] == SUB_INTENT_EXERCISE


@patch("chatbot.agents.triage.get_health_store")
@patch("chatbot.agents.triage.call_sealion")
@patch("chatbot.agents.triage._get_router")
def test_full_llm_fallback_chain_companion(mock_router, mock_llm, mock_store):
    """L1 SR miss → LLM 返回 companion → 直接路由，不进 L2。"""
    mock_router.return_value = _make_router(None)
    mock_llm.return_value    = _l1_json(INTENT_COMPANION)
    mock_store.return_value  = MagicMock()
    with patch("chatbot.agents.triage._classify_sub_intent") as mock_l2:
        result = triage_node(_state("就是想聊聊天"))
        mock_l2.assert_not_called()
    assert result["intent"]    == INTENT_COMPANION
    assert result["sub_intent"] is None


# ═══════════════════════════════════════════════════════════════════════
# 6. route_by_intent 四路分支
# ═══════════════════════════════════════════════════════════════════════

from chatbot.agents.triage import route_by_intent

@pytest.mark.parametrize("intent,expected_node", [
    (INTENT_CRISIS,    "crisis_agent"),
    (INTENT_MEDICAL,   "expert_agent"),
    (INTENT_HYBRID,    "hybrid_agent"),
    (INTENT_COMPANION, "companion_agent"),
    ("unknown",        "companion_agent"),   # 未知意图兜底
])
def test_route_by_intent(intent, expected_node):
    state = {"intent": intent}
    assert route_by_intent(state) == expected_node


# ═══════════════════════════════════════════════════════════════════════
# 7. Crisis Agent：4 种语言的响应内容
# ═══════════════════════════════════════════════════════════════════════

CRISIS_HOTLINE = "1767"   # SOS Singapore，所有语言版本都应包含

@pytest.mark.parametrize("lang_input,lang_code", [
    ("",       "en"),   # 无输入 → 默认英文
    ("我不想活了", "zh"),
    ("tidak mahu hidup", "ms"),
    ("வாழ விரும்பவில்லை", "ta"),
])
def test_crisis_agent_contains_hotline(lang_input, lang_code):
    """所有语言的危机响应都应包含 SOS 热线号码。"""
    state = {
        "user_id":       "test_user",
        "user_input":    lang_input,
        "emotion_label": "sad",
        "user_profile":  {},
    }
    result = crisis_agent_node(state)
    assert CRISIS_HOTLINE in result["response"], \
        f"语言={lang_code} 的响应缺少热线号码"
    assert result["emotion_log"]["is_crisis"] is True


def test_crisis_agent_never_calls_llm():
    """crisis_agent 不导入也不调用任何 LLM — 模块级验证。"""
    import chatbot.agents.crisis as crisis_module
    # crisis.py 不应 import call_sealion（固定响应，无需 LLM）
    assert not hasattr(crisis_module, "call_sealion"), \
        "crisis_agent 不应引入 call_sealion"


# ═══════════════════════════════════════════════════════════════════════
# 8. 边界情况
# ═══════════════════════════════════════════════════════════════════════

@patch("chatbot.agents.triage.get_health_store")
@patch("chatbot.agents.triage.call_sealion")
@patch("chatbot.agents.triage._get_router")
def test_empty_input_falls_to_companion(mock_router, mock_llm, mock_store):
    """空输入不崩溃，兜底 companion。"""
    mock_router.return_value = _make_router(None)
    mock_llm.return_value    = _l1_json(INTENT_COMPANION)
    mock_store.return_value  = MagicMock()
    result = triage_node(_state(""))
    assert result["intent"] in (INTENT_COMPANION, INTENT_MEDICAL, INTENT_CRISIS)


@patch("chatbot.agents.triage.get_health_store")
@patch("chatbot.agents.triage.call_sealion")
@patch("chatbot.agents.triage._get_router")
def test_sr_exception_falls_to_llm(mock_router, mock_llm, mock_store):
    """L1 SR 抛异常 → 不崩溃，进入 LLM 路径。"""
    bad_router = MagicMock()
    bad_router.side_effect = Exception("encoder crash")
    mock_router.return_value = bad_router
    mock_llm.return_value    = _l1_json(INTENT_COMPANION)
    mock_store.return_value  = MagicMock()
    result = triage_node(_state("你好"))
    assert result["intent"] in (INTENT_COMPANION, INTENT_MEDICAL, INTENT_CRISIS)


@patch("chatbot.agents.triage.get_health_store")
@patch("chatbot.agents.triage._prefetch_rag")
@patch("chatbot.agents.triage._get_sub_router")
@patch("chatbot.agents.triage._get_router")
def test_rag_prefetch_called_for_medical(mock_router, mock_sub, mock_rag, mock_store):
    """medical 意图命中后应触发 RAG 预取。"""
    mock_router.return_value = _make_router(INTENT_MEDICAL)
    mock_sub.return_value    = _make_router(SUB_INTENT_GLUCOSE)
    mock_store.return_value  = MagicMock()
    triage_node(_state("血糖9.5正常吗", emotion="neutral"))
    mock_rag.assert_called_once()


@patch("chatbot.agents.triage.get_health_store")
@patch("chatbot.agents.triage._get_router")
def test_rag_prefetch_not_called_for_companion(mock_router, mock_store):
    """companion 意图不触发 RAG 预取。"""
    mock_router.return_value = _make_router(INTENT_COMPANION)
    mock_store.return_value  = MagicMock()
    with patch("chatbot.agents.triage._prefetch_rag") as mock_rag:
        triage_node(_state("今天心情不好"))
        mock_rag.assert_not_called()


@patch("chatbot.agents.triage.get_health_store")
@patch("chatbot.agents.triage._get_router")
def test_rag_prefetch_not_called_for_crisis(mock_router, mock_store):
    """crisis 意图不触发 RAG 预取。"""
    mock_router.return_value = _make_router(INTENT_CRISIS)
    mock_store.return_value  = MagicMock()
    with patch("chatbot.agents.triage._prefetch_rag") as mock_rag:
        triage_node(_state("我不想活了"))
        mock_rag.assert_not_called()


@patch("chatbot.agents.triage.get_health_store")
@patch("chatbot.agents.triage._prefetch_rag")
@patch("chatbot.agents.triage._get_sub_router")
@patch("chatbot.agents.triage._get_router")
def test_emotion_logged_for_all_intents(mock_router, mock_sub, mock_rag, mock_store):
    """每次路由都应记录情绪 log。"""
    mock_store_instance = MagicMock()
    mock_store.return_value = mock_store_instance
    for intent, router_val in [
        (INTENT_CRISIS,    _make_router(INTENT_CRISIS)),
        (INTENT_COMPANION, _make_router(INTENT_COMPANION)),
        (INTENT_MEDICAL,   _make_router(INTENT_MEDICAL)),
    ]:
        mock_sub.return_value = _make_router(SUB_INTENT_GENERAL)
        mock_router.return_value = router_val
        triage_node(_state("test", emotion="neutral"))

    assert mock_store_instance.log_emotion.call_count == 3


# ═══════════════════════════════════════════════════════════════════════
# 9. state 字段完整性
# ═══════════════════════════════════════════════════════════════════════

@patch("chatbot.agents.triage.get_health_store")
@patch("chatbot.agents.triage._prefetch_rag")
@patch("chatbot.agents.triage._get_sub_router")
@patch("chatbot.agents.triage._get_router")
@pytest.mark.parametrize("intent,sub", [
    (INTENT_MEDICAL,   SUB_INTENT_GLUCOSE),
    (INTENT_HYBRID,    SUB_INTENT_FOOD),
])
def test_result_has_all_required_fields(mock_router, mock_sub, mock_rag, mock_store, intent, sub):
    """triage_node 返回值必须包含 intent / all_intents / sub_intent / emotion_label。"""
    mock_router.return_value = _make_router(INTENT_MEDICAL)
    mock_sub.return_value    = _make_router(sub)
    mock_store.return_value  = MagicMock()
    emotion = "fearful" if intent == INTENT_HYBRID else "neutral"
    result = triage_node(_state("血糖问题", emotion=emotion))

    assert "intent"       in result
    assert "all_intents"  in result
    assert "sub_intent"   in result
    assert "emotion_label" in result
    assert isinstance(result["all_intents"], list)
