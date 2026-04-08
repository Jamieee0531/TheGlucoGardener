"""
Companion Agent - warm emotional support for chronic illness patients.
Long-term memory: reads recent emotion summary injected into prompt.
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


def _fmt_vision_context(vision_result: list) -> str:
    """Build a one-line food context string from vision_result, if any."""
    if not vision_result:
        return ""
    for vr in vision_result:
        if vr.get("scene_type") == "FOOD" and not vr.get("error"):
            food_name = vr.get("food_name", "")
            cal = vr.get("total_calories", "")
            gi  = vr.get("gi_level", "")
            if food_name:
                parts = [food_name]
                if cal:
                    parts.append(f"\u7ea6{int(cal)}\u5927\u5361")
                if gi:
                    parts.append(f"{gi} GI")
                return "\uff0c".join(parts)
    return ""


def companion_agent_node(state: ChatState) -> dict:
    profile       = state.get("user_profile", {})
    name          = profile.get("name", "\u60a8")
    user_input    = state["user_input"]
    transcribed   = state.get("transcribed_text") or ""
    lang_source   = transcribed if transcribed.strip() else user_input
    language      = _detect_language(lang_source) if lang_source.strip() else profile.get("language", "Chinese")
    emotion_label = state.get("emotion_label", "neutral")
    user_id       = state["user_id"]

    # Long-term memory
    store           = get_health_store()
    emotion_context = store.format_memory_for_prompt(user_id, days=14)

    emotion_hint = f"[\u5f53\u524d\u60c5\u7eea]{emotion_label}\n" if emotion_label != "neutral" else ""

    # Food photo context
    food_context = _fmt_vision_context(state.get("vision_result") or [])
    if food_context:
        food_hint = (
            f"[\u7528\u6237\u4e0a\u4f20\u4e86\u98df\u7269\u7167\u7247]\u8bc6\u522b\u7ed3\u679c\uff1a{food_context}\n"
            "\u8bf7\u5728\u56de\u590d\u4e2d\u81ea\u7136\u5730\u63d0\u5230\u8fd9\u4e2a\u98df\u7269\uff08\u76f4\u63a5\u8bf4\u51fa\u540d\u79f0\uff09\u3002\n"
        )
    else:
        food_hint = ""

    system_prompt = (
        f"You are a warm, caring companion for {name}, a chronic illness patient in Singapore."
        f" Reply ENTIRELY in {language}, do not mix languages.\n"
        + (emotion_context + "\n" if emotion_context else "")
        + emotion_hint
        + food_hint
        + "How to respond:\n"
        "- Always respond to the SPECIFIC thing the user just said -- mirror their words, not generic comfort\n"
        "- Sound like a close friend texting, not a helpline bot\n"
        "- Keep it short: 1-2 sentences max\n"
        "- No hollow phrases: NEVER say 'I'm here for you', 'You're not alone', 'Take a deep breath', 'I understand'\n"
        "- No medical advice; if health topic comes up, gently acknowledge and ask one caring question\n"
        "- Don't repeat questions already asked in the conversation history\n"
        "- Vary your sentence starters every reply\n"
        "- Always end with a gentle open question to invite the user to keep sharing -- never leave the response closed\n"
        "- Example good reply to 'my daughter never calls': "
        "'Waiting for a call that never comes... that kind of quiet can feel so heavy lah."
        " Has it been like this for a while, or did something change recently?'\n"
        "- Example bad reply: 'I'm here for you. Take a deep breath.'"
    )

    history = format_history_for_sealion(state.get("history", []))
    history.append({"role": "user", "content": user_input})
    print("\n\u52a9\u624b\uff1a", end="", flush=True)
    response = call_sealion_with_history_stream(system_prompt, history)

    emotion_log = {
        "user_id": user_id, "timestamp": datetime.now().isoformat(),
        "input": user_input, "emotion_label": emotion_label,
        "agent_response": response, "is_crisis": False,
    }

    print(f"[\u964a\u4f34Agent] \u60c5\u7eea\uff1a{emotion_label}")
    return {"response": response, "emotion_log": emotion_log}
