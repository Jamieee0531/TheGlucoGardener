"""
agents/crisis.py
Crisis intervention node: triggered when abandonment-of-treatment or self-harm intent is detected.
Does not call the LLM; returns a fixed warm response + Singapore crisis hotlines.
"""
from datetime import datetime
from chatbot.state.chat_state import ChatState
from chatbot.memory.rag.lang_detect import detect_lang

_RESPONSES = {
    "en": (
        "Hey, I hear you — things must feel really heavy right now. "
        "You don't have to face this alone.\n\n"
        "Please reach out to someone who can help:\n"
        "- **SOS (Samaritans of Singapore)**: 1767 (24/7)\n"
        "- **IMH Crisis Helpline**: 6389 2222 (24/7)\n"
        "- **Emergency**: 995\n\n"
        "I'm still here whenever you want to talk."
    ),
    "zh": (
        "我听到你了，现在一定很难受。你不需要一个人扛着这些。\n\n"
        "请联系可以帮助你的人：\n"
        "- **新加坡撒玛利亚防自杀协会**：1767（24小时）\n"
        "- **IMH 危机热线**：6389 2222（24小时）\n"
        "- **紧急求助**：995\n\n"
        "我一直在这里，随时都可以跟我说话。"
    ),
    "ms": (
        "Saya dengar awak — mesti berat sangat sekarang. Awak tak perlu tanggung sorang-sorang.\n\n"
        "Sila hubungi seseorang yang boleh membantu:\n"
        "- **SOS (Samaritans of Singapore)**: 1767 (24 jam)\n"
        "- **IMH Crisis Helpline**: 6389 2222 (24 jam)\n"
        "- **Kecemasan**: 995\n\n"
        "Saya masih di sini bila awak nak berbual."
    ),
    "ta": (
        "நான் உங்களை கேட்கிறேன் — இப்போது மிகவும் கஷ்டமாக இருக்கும். "
        "நீங்கள் தனியாக இதை சுமக்க வேண்டியதில்லை.\n\n"
        "உதவி பெற தொடர்பு கொள்ளுங்கள்:\n"
        "- **SOS**: 1767 (24 மணி நேரமும்)\n"
        "- **IMH நெருக்கடி உதவி**: 6389 2222 (24 மணி நேரமும்)\n"
        "- **அவசரநிலை**: 995\n\n"
        "நான் இங்கே இருக்கிறேன், எப்போது வேண்டுமானாலும் பேசலாம்."
    ),
}


def crisis_agent_node(state: ChatState) -> dict:
    profile    = state.get("user_profile", {})
    user_input = state.get("user_input", "")
    lang_code  = detect_lang(profile.get("language") or user_input)
    response   = _RESPONSES.get(lang_code, _RESPONSES["en"])

    emotion_log = {
        "user_id":       state["user_id"],
        "timestamp":     datetime.now().isoformat(),
        "input":         user_input,
        "emotion_label": state.get("emotion_label", "neutral"),
        "agent_response": response,
        "is_crisis":     True,
    }

    print(f"[Crisis Agent] crisis intervention triggered | language: {lang_code}")
    return {"response": response, "emotion_log": emotion_log}
