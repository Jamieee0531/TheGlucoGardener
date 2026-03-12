"""
Policy层，不调LLM
- 只记录负面情绪日志（sad/anxious/angry）
- 生成情绪上下文描述供 agent 参考（非强制指令）
- 心理危机的硬编码 alert 在 companion.py 中处理
"""
from chatbot.state.chat_state import ChatState

NEGATIVE_EMOTIONS = ["sad", "anxious", "angry"]


def policy_node(state: ChatState) -> dict:
    emotion = state.get("emotion_label", "neutral")

    # 只记录负面情绪，中性/正面不写入
    recent_emotions = state.get("recent_emotions", [])
    if emotion in NEGATIVE_EMOTIONS:
        recent_emotions = (recent_emotions + [emotion])[-5:]

    # 生成上下文描述（给 agent 作参考，不是强制规则）
    policy_instruction = f"用户当前情绪：{emotion}" if emotion != "neutral" else ""

    print(f"[Policy] 情绪：{emotion} | 上下文：{policy_instruction or '无'}")
    return {
        "policy_instruction": policy_instruction,
        "recent_emotions":    recent_emotions,
        "persistent_alert":   None,
    }
