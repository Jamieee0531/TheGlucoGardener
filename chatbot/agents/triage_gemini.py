"""
agents/triage_gemini.py
OpenAI 统一分诊：单次调用同时输出 intent + emotion + emotion_intensity

文字输入：OpenAI → intent + emotion + emotion_intensity（不调 MERaLiON）
语音输入：MERaLiON → emotion_label（input_node 已完成）；OpenAI → intent + emotion_intensity
"""
from chatbot.state.chat_state import ChatState
from chatbot.utils.llm_factory import call_openai_json
from chatbot.memory.long_term import get_health_store
from chatbot.config.settings import (
    INTENT_COMPANION, INTENT_MEDICAL, INTENT_CRISIS, INTENT_HYBRID,
)
from chatbot.agents.triage import _prefetch_rag, input_node  # input_node 完全复用

# ── Schema ────────────────────────────────────────────────────────────
_CLASSIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {
            "type": "string",
            "enum": ["crisis", "medical", "companion", "hybrid"],
        },
        "emotion": {
            "type": "string",
            "enum": ["angry", "sad", "fearful", "happy", "neutral"],
        },
        "emotion_intensity": {
            "type": "string",
            "enum": ["none", "mild", "high"],
        },
        "reasoning": {"type": "string"},
    },
    "required": ["intent", "emotion", "emotion_intensity", "reasoning"],
    "additionalProperties": False,
}

_CLASSIFY_PROMPT = """\
你是新加坡慢性病健康助手的分诊系统。根据用户消息，返回 JSON。

intent 规则：
- crisis    ：放弃治疗、自伤、活着没意思（注意：身体疲劳/睡眠差等躯体症状不是 crisis）
- hybrid    ：情绪困扰是主要诉求，医疗问题是次要的（如刚确诊很崩溃、长期带病很累很绝望）；若用户主要在描述症状或寻求医疗建议，即使带有轻微焦虑，仍归为 medical
- medical   ：有具体医疗问题/寻求建议/描述症状（含：食物能不能吃、GI值、血糖数值、用药、运动、并发症、本地医疗资源等）
- companion ：纯情绪倾诉、感慨、抱怨、闲聊、问候，没有具体问题需要回答

emotion 规则：
- 识别用户整体情绪基调：angry / sad / fearful / happy / neutral

emotion_intensity 规则（描述情绪强烈程度，与 intent 无关）：
- none ：情绪平稳，无明显情绪色彩
- mild ：有一定情绪但不强烈，可以同时回应情绪和医疗需求
- high ：情绪明显强烈，回复应以情感支持为主，医疗内容保持简短

用户消息：
"""


def triage_node_gemini(state: ChatState) -> dict:
    """OpenAI 统一分诊节点。"""
    user_input = state["user_input"]
    is_voice   = state.get("input_mode", "text") == "voice"

    # 如果有图片上传，直接路由到 expert（食物/药物/报告分析都需要专业知识）
    if state.get("image_paths") or state.get("vision_result"):
        print("[Triage] image detected → force expert")
        _prefetch_rag(state["user_id"], user_input)
        return {
            "intent":             INTENT_MEDICAL,
            "all_intents":        [INTENT_MEDICAL],
            "emotion_label":      "neutral",
            "emotion_confidence": 1.0,
            "emotion_intensity":  "none",
        }

    # OpenAI 分类（文字 + 语音都调用，intent 和 emotion_intensity 都从这里来）
    try:
        result            = call_openai_json(_CLASSIFY_PROMPT + user_input, _CLASSIFY_SCHEMA)
        intent            = result.get("intent", "companion")
        llm_emotion       = result.get("emotion", "neutral")
        emotion_intensity = result.get("emotion_intensity", "none")
        reasoning         = result.get("reasoning", "")
        print(f"[Triage] {intent} | {llm_emotion} ({emotion_intensity}) | {reasoning[:60]}")
    except Exception as e:
        print(f"[Triage] OpenAI 调用失败（{e}），降级为 companion")
        intent, llm_emotion, emotion_intensity = "companion", "neutral", "none"

    # 语音：MERaLiON 的 emotion_label 更准（有音频特征），覆盖 LLM emotion
    # 文字：直接用 LLM emotion
    if is_voice:
        emotion_label      = state.get("emotion_label", "neutral")
        emotion_confidence = state.get("emotion_confidence", 0.0)
    else:
        emotion_label      = llm_emotion
        emotion_confidence = 1.0  # LLM 不给置信度，标记为 1.0

    get_health_store().log_emotion(state["user_id"], emotion_label, user_input)

    if intent == INTENT_CRISIS:
        return {
            "intent":             INTENT_CRISIS,
            "all_intents":        [INTENT_CRISIS],
            "emotion_label":      emotion_label,
            "emotion_confidence": emotion_confidence,
            "emotion_intensity":  emotion_intensity,
        }

    if intent in (INTENT_MEDICAL, INTENT_HYBRID):
        _prefetch_rag(state["user_id"], user_input)

    return {
        "intent":             intent,
        "all_intents":        [intent],
        "emotion_label":      emotion_label,
        "emotion_confidence": emotion_confidence,
        "emotion_intensity":  emotion_intensity,
    }
