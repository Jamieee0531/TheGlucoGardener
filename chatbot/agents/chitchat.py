"""
闲聊Agent，用Qwen对话模型
轻量日常对话
"""
from chatbot.state.chat_state import ChatState
from chatbot.utils.llm_factory import call_sealion_with_history_stream, format_history_for_sealion


def chitchat_agent_node(state: ChatState) -> dict:
    profile  = state.get("user_profile", {})
    name     = profile.get("name", "您")
    language = profile.get("language", "Chinese")

    system_prompt = f"""你是友善的健康助手，与新加坡慢性病患者进行日常对话。
患者姓名：{name}，请用{language}回复。
轻松自然，像朋友聊天，偶尔关心患者日常状态，回复80字以内。"""

    history = format_history_for_sealion(state.get("history", []))
    history.append({"role": "user", "content": state["user_input"]})
    print("\n助手：", end="", flush=True)
    response = call_sealion_with_history_stream(system_prompt, history)

    print(f"[闲聊Agent] 回复完成")
    return {"response": response}
