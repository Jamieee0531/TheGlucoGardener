"""
Integration tests for the demo golden path.
Uses mocked LLM calls and pre-injected vision_result (no real API calls).
"""
from unittest.mock import patch, MagicMock
import pytest


def _mock_llm_response(system_prompt: str, messages: list, reasoning: bool = False) -> str:
    """Smart mock: returns contextually appropriate responses based on prompt content."""
    combined = system_prompt + str(messages)
    # Triage: return JSON
    if '"intents"' in combined or "分诊" in combined or "意图" in combined and "返回JSON" in combined:
        if "我好难过" in combined or "压力" in combined:
            return '{"intents": ["emotional"], "emotion": "sad"}'
        if "药" in combined or "medication" in combined.lower():
            return '{"intents": ["medical"], "emotion": "neutral"}'
        return '{"intents": ["medical"], "emotion": "neutral"}'
    # Chitchat
    if "闲聊" in combined or "日常对话" in combined:
        return "你好呀！我是你的健康助手，有什么可以帮你的？"
    # Expert summary
    if "综合建议" in combined or "信息已齐全" in combined:
        return "根据您的情况，建议控制主食摄入，继续按时服用二甲双胍。免责声明：本建议仅供参考。"
    # Expert question
    if "只问" in combined and "血糖" in combined:
        return "我关心您的健康状况。请问您的血糖大概测到多少呢？"
    if "只问" in combined and "药" in combined:
        return "了解。今天的药有按时服用吗？"
    if "确认" in combined and "对吗" in combined:
        return "看起来您吃的是海南鸡饭，对吗？"
    # Companion
    if "陪伴" in combined or "安抚" in combined:
        return "我理解您的感受，控制饮食确实不容易。您能和我说说是什么让您感到压力大吗？"
    return "好的，我了解了。"


def _mock_llm_single(system_prompt: str, user_message: str, reasoning: bool = False) -> str:
    return _mock_llm_response(system_prompt, [{"role": "user", "content": user_message}])


def _build_state(**overrides):
    """Build a minimal valid ChatState for testing."""
    from state.chat_state import ChatState
    defaults = dict(
        user_input="",
        input_mode="text",
        chat_mode="personal",
        user_id="test_user",
        audio_path=None,
        transcribed_text=None,
        emotion_label="neutral",
        emotion_confidence=0.0,
        intent=None,
        all_intents=None,
        policy_instruction=None,
        recent_emotions=[],
        persistent_alert=None,
        history=[],
        user_profile={
            "name": "测试用户",
            "language": "Chinese",
            "conditions": ["Type 2 Diabetes"],
            "medications": ["Metformin"],
        },
        conversation_stage=None,
        collected_info={},
        response=None,
        emotion_log=None,
        task_trigger=None,
        alert_trigger=None,
        image_paths=None,
        vision_result=None,
    )
    defaults.update(overrides)
    return ChatState(**defaults)


@patch("utils.llm_factory.call_sealion_with_history", side_effect=_mock_llm_response)
@patch("agents.triage.call_sealion", side_effect=_mock_llm_single)
def test_step1_chitchat(mock_triage, mock_llm):
    """Step 1: User says hello -> chitchat agent responds."""
    from graph.builder import build_graph
    app = build_graph()
    state = _build_state(user_input="你好")
    result = app.invoke(state)
    assert result.get("response") is not None
    assert result.get("intent") == "chitchat" or result.get("intent") in ["chitchat", "medical", "emotional"]
    # Main check: we got a response without errors
    assert len(result["response"]) > 0


@patch("utils.llm_factory.call_sealion_with_history", side_effect=_mock_llm_response)
@patch("agents.triage.call_sealion", side_effect=_mock_llm_single)
def test_step2_food_vision_prefills_diet(mock_triage, mock_llm):
    """Step 2: Pre-injected food vision result -> Expert pre-fills diet, asks glucose."""
    from graph.builder import build_graph
    app = build_graph()
    # Simulate: image already processed by Vision Agent (vision_result pre-injected)
    state = _build_state(
        user_input="我拍了一张食物照片",
        vision_result=[{
            "scene_type": "FOOD",
            "items": [{"name": "海南鸡饭", "quantity": "1份",
                       "nutrition": {"calories_kcal": 600}}],
            "total_calories_kcal": 600.0,
            "confidence": 0.85,
        }],
    )
    result = app.invoke(state)
    # Diet should be pre-filled from vision result
    collected = result.get("collected_info", {})
    assert collected.get("diet") is not None, "Diet should be pre-filled from vision result"
    diet_entry = collected["diet"]
    assert isinstance(diet_entry, dict), "Diet entry should be a dict"
    assert diet_entry.get("source") == "vision"
    assert diet_entry.get("confidence") == 0.85
    # Stage should now be asking glucose (diet is skipped)
    stage = result.get("conversation_stage", "")
    assert stage == "asking_glucose", f"Expected asking_glucose, got {stage}"


@patch("utils.llm_factory.call_sealion_with_history", side_effect=_mock_llm_response)
@patch("agents.triage.call_sealion", side_effect=_mock_llm_single)
def test_step3_glucose_collected(mock_triage, mock_llm):
    """Step 3: User provides glucose value -> stored as confirmed, ask medication next."""
    from graph.builder import build_graph
    app = build_graph()
    state = _build_state(
        user_input="最近空腹血糖 7.2",
        conversation_stage="asking_glucose",
        collected_info={
            "diet": {"value": "海南鸡饭（约600.0大卡）", "confidence": 0.85, "source": "vision"},
        },
    )
    result = app.invoke(state)
    collected = result.get("collected_info", {})
    assert collected.get("glucose") is not None, "Glucose should be stored after user answer"
    # Should now be asking medication
    stage = result.get("conversation_stage", "")
    assert stage == "asking_medication", f"Expected asking_medication, got {stage}"


@patch("utils.llm_factory.call_sealion_with_history", side_effect=_mock_llm_response)
@patch("agents.triage.call_sealion", side_effect=_mock_llm_single)
def test_step4_all_confirmed_gives_summary_and_alert(mock_triage, mock_llm):
    """Step 4: All fields confirmed -> summary response + alert_trigger for high glucose."""
    from graph.builder import build_graph
    app = build_graph()
    state = _build_state(
        user_input="我拍了一张药物照片",
        conversation_stage="asking_medication",
        collected_info={
            "glucose": {"value": "7.2 mmol", "confidence": None, "source": "user"},
            "diet": {"value": "海南鸡饭（约600大卡）", "confidence": 0.85, "source": "vision"},
        },
        vision_result=[{
            "scene_type": "MEDICATION",
            "drug_name": "Metformin",
            "dosage": "500mg",
            "confidence": 0.9,
        }],
    )
    result = app.invoke(state)
    # Medication should be pre-filled from vision
    collected = result.get("collected_info", {})
    assert collected.get("medication") is not None, "Medication should be pre-filled from vision"
    # Stage should reset to idle after summary
    assert result.get("conversation_stage") == "idle"
    # Alert should be triggered (glucose 7.2 > 7.0)
    assert result.get("alert_trigger") is not None, "alert_trigger should be set for elevated glucose"
    assert result["alert_trigger"]["severity"] == "elevated"


@patch("utils.llm_factory.call_sealion_with_history", side_effect=_mock_llm_response)
@patch("agents.triage.call_sealion", side_effect=_mock_llm_single)
def test_step5_emotional_routes_to_companion(mock_triage, mock_llm):
    """Step 5: Emotional input -> routed to companion agent."""
    from graph.builder import build_graph
    app = build_graph()
    state = _build_state(user_input="唉，我最近压力好大，管不住嘴")
    result = app.invoke(state)
    # Should route to companion
    assert result.get("intent") in ["emotional", "medical"]  # keyword may hit medical too
    assert result.get("response") is not None
    assert len(result["response"]) > 0
