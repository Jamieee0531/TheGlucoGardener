"""
agents/triage.py
意图分类 + 情绪识别合并为一次调用
追问链进行中：只检测退出意图，不判断情绪（省token）
"""
import json
import re
import concurrent.futures
from typing import Optional
from chatbot.state.chat_state import ChatState
from chatbot.utils.llm_factory import call_sealion
from chatbot.utils.meralion import process_voice_input, process_text_input
from chatbot.config.settings import ALL_INTENTS, INTENT_COMPANION
from chatbot.memory.long_term import get_health_store

# ── RAG 预取：medical 命中后立即后台拉取，存 future 供 expert_agent 消费 ──
_rag_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
_rag_futures: dict = {}   # session_id → Future[str]

from src.vision_agent.agent import VisionAgent as _VisionAgent
from src.vision_agent.config import get_settings, VLMProvider
from src.vision_agent.llm.gemini import GeminiVLM
from src.vision_agent.llm.mock import MockVLM
from src.vision_agent.llm.sealion import SeaLionVLM

_vision_agent: "_VisionAgent | None" = None
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)


def _build_vlm():
    """Build VLM based on .env config (VLM_PROVIDER)."""
    provider = get_settings().vlm_provider
    if provider == VLMProvider.GEMINI:
        return GeminiVLM()
    if provider == VLMProvider.SEALION:
        return SeaLionVLM()
    return MockVLM()


def analyze_image(image_path: str):
    """Call Vision Agent to analyze an image. Returns AnalysisResult or None on timeout."""
    global _vision_agent
    if _vision_agent is None:
        _vision_agent = _VisionAgent(vlm=_build_vlm())
    future = _executor.submit(_vision_agent.analyze, image_path)
    try:
        return future.result(timeout=30)
    except concurrent.futures.TimeoutError:
        print(f"[Triage] Vision 超时（>30s），跳过图片分析：{image_path}")
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

        return {
            "user_input":         result["transcribed_text"],
            "transcribed_text":   result["transcribed_text"],
            "emotion_label":      result["emotion_label"],
            "emotion_confidence": result["emotion_confidence"],
        }

    # ── Image handling ──────────────────────────────────
    image_paths = state.get("image_paths") or []
    vision_result = []
    print(f"[input_node] image_paths={image_paths}")

    if image_paths:
        for path in image_paths:
            try:
                print(f"[input_node] calling analyze_image({path})")
                result = analyze_image(path)
                print(f"[input_node] analyze_image returned: {result}")
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
                print(f"[input_node] ❌ Vision 异常：{type(e).__name__}: {e}")
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

    # ── 文字情绪识别（语义）────────────────────────────────
    emotion_result = process_text_input(user_input)

    updates = {
        "transcribed_text":   user_input,
        "emotion_label":      emotion_result["emotion_label"],
        "emotion_confidence": emotion_result["emotion_confidence"],
        # Always reset vision_result so stale data from the previous turn
        # does not bleed into text-only follow-up messages.
        "vision_result":      vision_result,
    }

    if image_paths:
        updates["user_input"] = user_input

    return updates


def triage_node(state: ChatState) -> dict:
    return _full_triage(state)



# ── Keyword pre-classification ────────────────────────────────────────────
# 只识别 medical（路由到 expert），其余由 companion 兜底
KEYWORD_RULES = [
    ("medical", [
        "血糖", "glucose", "sugar", "药", "medicine", "metformin",
        "二甲双胍", "饮食", "diet", "吃了什么", "GI", "升糖", "HbA1c", "hba1c",
        "糖化", "胰岛素", "insulin", "blood pressure", "血压", "症状", "symptom",
    ]),
]

def keyword_preclassify(user_input: str) -> Optional[str]:
    """Classify intent by keywords. Returns intent string or None (fall back to LLM)."""
    text = user_input.lower()
    for intent, keywords in KEYWORD_RULES:
        for kw in keywords:
            if re.search(kw, text):
                return intent
    return None


def _full_triage(state: ChatState) -> dict:
    """意图判断：关键词预分类 + LLM兜底。情绪由 input_node 已通过 MERaLiON 设好。"""
    emotion_label = state.get("emotion_label", "neutral")
    user_input    = state["user_input"]

    # ── Step 0: Food/medication/report photo → always medical ──
    vision_result = state.get("vision_result") or []
    if vision_result:
        top_scene = vision_result[0].get("scene_type", "UNKNOWN")
        if top_scene in ("FOOD", "MEDICATION", "REPORT"):
            get_health_store().log_emotion(state["user_id"], emotion_label, user_input)
            _prefetch_rag(state["user_id"], user_input)
            print(f"[Triage] 图片{top_scene}→medical | 情绪：{emotion_label}")
            return {
                "intent":        "medical",
                "all_intents":   ["medical"],
                "emotion_label": emotion_label,
            }

    # ── Step 1: Try keyword pre-classification ──────────
    keyword_intent = keyword_preclassify(user_input)
    if keyword_intent:
        get_health_store().log_emotion(state["user_id"], emotion_label, user_input)
        print(f"[Triage] 关键词命中：{keyword_intent} | 情绪：{emotion_label}")
        if keyword_intent == "medical":
            _prefetch_rag(state["user_id"], user_input)
        return {
            "intent":        keyword_intent,
            "all_intents":   [keyword_intent],
            "emotion_label": emotion_label,
        }

    # ── Step 2: LLM 只判意图，情绪用关键词 ──────────────
    system_prompt = """你是医疗健康助手的分诊系统，服务于新加坡的慢性病患者。
结合【最近对话】和【当前消息】，判断用户意图，返回JSON：
{"intents": ["标签"]}

意图标签（二选一）：
- medical    （血糖、血压、药物、饮食建议、症状、身体不适等任何健康医疗话题）
- companion  （情绪倾诉、日常闲聊、问候、确认词、其他非医疗话题）

规则：
- 只返回一个标签
- 有任何医疗/健康相关内容，优先归为 medical
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
        intents = [INTENT_COMPANION]

    get_health_store().log_emotion(state["user_id"], emotion_label, user_input)
    print(f"[Triage] 意图：{intents} | 情绪：{emotion_label}")
    if intents[0] == "medical":
        _prefetch_rag(state["user_id"], user_input)
    return {
        "intent":        intents[0],
        "all_intents":   intents,
        "emotion_label": emotion_label,
    }


def route_by_intent(state: ChatState) -> str:
    intent = state.get("intent", "companion")
    return "expert_agent" if intent == "medical" else "companion_agent"


def _prefetch_rag(user_id: str, query: str) -> None:
    """在后台线程开始 RAG 检索，结果缓存供 expert_agent 消费。"""
    from chatbot.memory.rag.retriever import get_retriever
    future = _rag_executor.submit(get_retriever().retrieve, query, 3)
    _rag_futures[user_id] = future


def consume_rag_prefetch(user_id: str, fallback_query: str) -> str:
    """Expert agent 调用：拿预取结果（已完成则零延迟），否则同步检索。"""
    future = _rag_futures.pop(user_id, None)
    if future:
        try:
            return future.result(timeout=5)
        except Exception:
            pass
    from chatbot.memory.rag.retriever import get_retriever
    return get_retriever().retrieve(fallback_query, 3)
