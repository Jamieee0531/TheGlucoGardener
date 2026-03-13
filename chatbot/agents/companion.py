"""
陪伴Agent，用Qwen对话模型
接收policy指令决定回复风格
长期记忆：读取近期情绪摘要注入 prompt（写入由 23:59 daily job 负责）
"""
from datetime import datetime
from chatbot.state.chat_state import ChatState
from chatbot.utils.llm_factory import (
    call_sealion_with_history_stream, format_history_for_sealion
)
from chatbot.memory.long_term import get_health_store


def companion_agent_node(state: ChatState) -> dict:
    profile            = state.get("user_profile", {})
    name               = profile.get("name", "您")
    language           = profile.get("language", "Chinese")
    user_input         = state["user_input"]
    emotion_label      = state.get("emotion_label", "neutral")
    policy_instruction = state.get("policy_instruction", "")
    user_id            = state["user_id"]

    # ── 读取近期情绪摘要（长期记忆）────────────────────────────
    store           = get_health_store()
    emotion_context = store.format_emotion_summary_for_llm(user_id, days=14)

    system_prompt = (
        f"你是温暖、有耐心的健康陪伴助手，陪伴新加坡的慢性病患者。\n"
        f"患者姓名：{name}，请用{language}回复。\n"
        f"{emotion_context + chr(10) if emotion_context else ''}"
        f"{f'【用户当前状态】{policy_instruction}' + chr(10) if policy_instruction else ''}"
        "通用原则：\n"
        "- 回复60字以内，越短越好\n"
        "- 不提供具体医疗建议\n"
        "- 不一定每次都要问问题，有时候只是陪着就够了\n"
        "- 像朋友一样说话，不要像顾问"
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
