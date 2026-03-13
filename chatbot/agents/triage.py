"""
agents/triage.py
意图分类 + 情绪识别合并为一次调用
追问链进行中：只检测退出意图，不判断情绪（省token）
"""
import json
from typing import Optional
from chatbot.state.chat_state import ChatState
from chatbot.utils.llm_factory import call_sealion
from chatbot.utils.meralion import process_voice_input
from chatbot.config.settings import ALL_INTENTS, INTENT_CHITCHAT
from chatbot.memory.long_term import get_health_store


import concurrent.futures

from src.vision_agent.agent import VisionAgent as _VisionAgent
_vision_agent: "_VisionAgent | None" = None
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)


def analyze_image(image_path: str):
    """Call Vision Agent to analyze an image. Returns AnalysisResult or None on timeout."""
    global _vision_agent
    if _vision_agent is None:
        _vision_agent = _VisionAgent()
    future = _executor.submit(_vision_agent.analyze, image_path)
    try:
        return future.result(timeout=15)
    except concurrent.futures.TimeoutError:
        print(f"[Triage] Vision 超时（>15s），跳过图片分析：{image_path}")
        return None
    except Exception as e:
        print(f"[Triage] Vision 调用失败：{e}")
        return None


# scene_type → synthetic text (when user sends image with no text)
SCENE_TEXT_MAP = {
    "FOOD":       "我拍了一张食物照片",
    "MEDICATION": "我拍了一张药物照片",
    "REPORT":     "我拍了一张化验单照片",
    "UNKNOWN":    "我发了一张照片",
}



def input_node(state: ChatState) -> dict:
    # ── Voice mode ──────────────────────────────────────
    if state["input_mode"] == "voice":
        audio_path = state.get("audio_path", "")
        result = process_voice_input(audio_path)

        # 写入语音情绪日志（confidence 门控）
        if result["emotion_confidence"] >= 0.6:
            get_health_store().upsert_emotion_log(
                state["user_id"], result["emotion_label"]
            )

        return {
            "user_input":         result["transcribed_text"],
            "transcribed_text":   result["transcribed_text"],
            "emotion_label":      result["emotion_label"],
            "emotion_confidence": result["emotion_confidence"],
        }

    # ── Image handling ──────────────────────────────────
    image_paths = state.get("image_paths") or []
    vision_result = []

    if image_paths:
        for path in image_paths:
            try:
                result = analyze_image(path)
                if result is None:
                    vision_result.append({
                        "scene_type": "UNKNOWN",
                        "error": "Vision 超时或失败",
                        "confidence": 0.0,
                    })
                elif not result.is_error and result.structured_output:
                    vision_result.append(result.structured_output.model_dump())
                else:
                    vision_result.append({
                        "scene_type": "UNKNOWN",
                        "error": result.error or "识别失败",
                        "confidence": 0.0,
                    })
            except Exception as e:
                vision_result.append({
                    "scene_type": "UNKNOWN",
                    "error": str(e),
                    "confidence": 0.0,
                })

    # ── Synthetic text for image-only input ─────────────
    user_input = state["user_input"]
    if image_paths and not user_input.strip():
        scene = vision_result[0].get("scene_type", "UNKNOWN") if vision_result else "UNKNOWN"
        user_input = SCENE_TEXT_MAP.get(scene, "我发了一张照片")

    updates = {
        "transcribed_text":   user_input,
        "emotion_label":      "neutral",
        "emotion_confidence": 0.0,
    }

    if image_paths:
        updates["user_input"] = user_input
        updates["vision_result"] = vision_result

    return updates


def triage_node(state: ChatState) -> dict:
    return _full_triage(state)



# ── Keyword pre-classification ────────────────────────────────────────────
# Checked before LLM call. Order matters: alert > medical > emotional > task.
KEYWORD_RULES = [
    ("medical", [
        "血糖", "glucose", "sugar", "药", "medicine", "metformin",
        "二甲双胍", "饮食", "diet", "吃了什么", "GI", "升糖",
    ]),
    ("emotional", [
        "难过", "伤心", "压力", "焦虑", "害怕", "孤独", "stress",
        "担心", "不开心", "depressed", "anxious",
    ]),
]

def keyword_preclassify(user_input: str) -> Optional[str]:
    """Classify intent by keywords. Returns intent string or None (fall back to LLM)."""
    import re
    text = user_input.lower()
    for intent, keywords in KEYWORD_RULES:
        for kw in keywords:
            if re.search(kw, text):
                return intent
    return None


def resolve_emotion(
    voice_emotion: str,
    voice_confidence: float,
    input_mode: str,
) -> str:
    """Unified emotion resolution: voice >= 0.6 → use result, otherwise neutral."""
    if input_mode == "voice" and voice_confidence >= 0.6:
        return voice_emotion
    return "neutral"


def _full_triage(state: ChatState) -> dict:
    """意图判断：关键词预分类 + LLM兜底。情绪只用关键词或语音模型，不走LLM。"""
    emotion_label      = state.get("emotion_label", "neutral")
    emotion_confidence = state.get("emotion_confidence", 0.0)
    input_mode         = state.get("input_mode", "text")
    user_input         = state["user_input"]

    # ── Step 1: Try keyword pre-classification ──────────
    keyword_intent = keyword_preclassify(user_input)
    if keyword_intent:
        emotion = resolve_emotion(emotion_label, emotion_confidence, input_mode)
        print(f"[Triage] 关键词命中：{keyword_intent} | 情绪：{emotion}")
        return {
            "intent":        keyword_intent,
            "all_intents":   [keyword_intent],
            "emotion_label": emotion,
        }

    # ── Step 2: LLM 只判意图，情绪用关键词 ──────────────
    system_prompt = """你是医疗健康助手的分诊系统，服务于新加坡的慢性病患者。
结合【最近对话】和【当前消息】，判断用户意图，返回JSON：
{"intents": ["标签1","标签2"]}

意图标签（按优先级，可多选）：
- medical    （血糖偏高、药物、饮食建议、症状、身体不适）
- emotional  （情绪倾诉、担心、沮丧、孤独、失望、需要陪伴）
- chitchat   （日常闲聊）

规则：
- 纯礼貌/确认词（谢谢、好的、嗯、明白、收到、thanks、ok 等）无论上下文如何，始终归为 ["chitchat"]
- 结合上下文：若前几轮是情绪话题，简短回应也归为emotional
- 身体不适（头晕、胸痛等紧急症状）归为 ["medical", "emotional"]
- 只返回JSON，不要任何解释"""

    history = state.get("history", [])
    recent  = history[-4:] if len(history) >= 4 else history
    context = ""
    if recent:
        context = "【最近对话】\n"
        for h in recent:
            role     = "用户" if h["role"] == "user" else "助手"
            context += f"{role}：{h['content']}\n"
        context += "\n【当前消息】\n"

    raw = call_sealion(system_prompt, context + user_input)

    try:
        clean   = raw.strip().replace("```json","").replace("```","").strip()
        data    = json.loads(clean)
        intents = [i for i in data.get("intents", []) if i in ALL_INTENTS]
    except Exception:
        intents = []

    if not intents:
        intents = [INTENT_CHITCHAT]

    # 情绪：voice >= 0.6 用模型结果，否则 neutral
    emotion = resolve_emotion(emotion_label, emotion_confidence, input_mode)

    print(f"[Triage] 意图：{intents} | 情绪：{emotion} | 输入：{input_mode}")
    return {
        "intent":        intents[0],
        "all_intents":   intents,
        "emotion_label": emotion,
    }


def route_by_intent(state: ChatState) -> str:
    route_map = {
        "emotional": "companion_agent",
        "medical":   "expert_agent",
        "chitchat":  "chitchat_agent",
    }
    return route_map.get(state.get("intent", "chitchat"), "chitchat_agent")
