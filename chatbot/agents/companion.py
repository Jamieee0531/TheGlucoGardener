"""
陪伴Agent，用Qwen对话模型
长期记忆：读取近期情绪摘要注入 prompt（写入由 23:59 daily job 负责）
"""
import re
from datetime import datetime
from chatbot.state.chat_state import ChatState
from chatbot.utils.llm_factory import (
    call_sealion_with_history_stream, format_history_for_sealion
)
from chatbot.memory.long_term import get_health_store


def _detect_language(text: str) -> str:
    """Detect if input is primarily English or Chinese."""
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    ascii_letters  = len(re.findall(r'[a-zA-Z]', text))
    return "English" if ascii_letters > chinese_chars else "Chinese"


def companion_agent_node(state: ChatState) -> dict:
    profile            = state.get("user_profile", {})
    name               = profile.get("name", "您")
    user_input         = state["user_input"]
    language           = _detect_language(user_input) if user_input.strip() else profile.get("language", "Chinese")
    emotion_label = state.get("emotion_label", "neutral")
    user_id       = state["user_id"]

    # ── 读取近期情绪摘要（长期记忆）────────────────────────────
    store           = get_health_store()
    emotion_context = store.format_emotion_summary_for_llm(user_id, days=14)

    emotion_hint = f"【当前情绪】{emotion_label}\n" if emotion_label != "neutral" else ""

    system_prompt = (
        f"You are a warm, caring companion for {name}, a chronic illness patient in Singapore. Reply ENTIRELY in {language}, do not mix languages.\n"
        f"{emotion_context + chr(10) if emotion_context else ''}"
        f"{emotion_hint}"
        "How to respond:\n"
        "- Always respond to the SPECIFIC thing the user just said — mirror their words, not generic comfort\n"
        "- Sound like a close friend texting, not a helpline bot\n"
        "- Keep it short: 1-2 sentences max\n"
        "- No hollow phrases: NEVER say 'I'm here for you', 'You're not alone', 'Take a deep breath', 'I understand'\n"
        "- No medical advice; if health topic comes up, gently acknowledge and ask one caring question\n"
        "- Don't repeat questions already asked in the conversation history\n"
        "- Vary your sentence starters every reply\n"
        "- Example good reply to 'my daughter never calls': 'Waiting for a call that never comes… that kind of quiet can feel so heavy lah.'\n"
        "- Example good reply when user asks you to help write a message: 'How about: \"Haven\\'t heard your voice in a while lah, miss you.\" Short and real — she\\'ll feel it one.'\n"
        "- Example bad reply: 'I'm here for you. Take a deep breath.'\n"
        "- Example bad reply when suggesting a message: 'Just thinking of you. Hope you\\'re doing well!' — too generic, no warmth"
    )

    history = format_history_for_sealion(state.get("history", []))
    history.append({"role": "user", "content": user_input})
    print("\n助手：", end="", flush=True)
    response = call_sealion_with_history_stream(system_prompt, history)

    emotion_log = {
        "user_id": user_id, "timestamp": datetime.now().isoformat(),
        "input": user_input, "emotion_label": emotion_label,
        "agent_response": response, "is_crisis": False,
    }

    print(f"[陪伴Agent] 情绪：{emotion_label}")
    return {"response": response, "emotion_log": emotion_log}
