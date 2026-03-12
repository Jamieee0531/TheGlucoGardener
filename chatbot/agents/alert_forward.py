"""
不调LLM
判断严重程度生成alert_trigger字典
等alert模块接收
"""
from datetime import datetime
from chatbot.state.chat_state import ChatState


def alert_forward_node(state: ChatState) -> dict:
    """
    预警转发 Agent：
    - 立即给用户安抚回复
    - 生成 alert_trigger → Julia 的预警模块
    - 不需要 LLM，速度要快
    """
    profile       = state.get("user_profile", {})
    language      = profile.get("language", "Chinese")
    emotion_label = state.get("emotion_label", "neutral")

    # 根据输入内容判断紧急程度
    alert_input = state["user_input"]
    is_critical = any(keyword in alert_input for keyword in [
        "18", "19", "20", "胸口痛", "胸痛", "头很晕", "发抖", "虚弱", "出汗",
        "chest", "dizzy", "shaking", "faint", "995"
    ])

    if is_critical:
        if language == "English":
            response = (
                "This sounds serious — please call 995 or go to A&E immediately! 🚨 "
                "Do not wait. I've notified your health monitoring system right away. "
                "If someone is with you, ask them for help now."
            )
        else:
            response = (
                "您的情况听起来很紧急，请立即拨打 995 或前往急诊！🚨 "
                "不要等待，我已立即通知您的健康监护系统。"
                "如果身边有人，请马上告诉他们。"
            )
    elif emotion_label in ["anxious", "scared"]:
        if language == "English":
            response = (
                "I hear you, please stay calm 🙏 "
                "I've notified your health monitoring system right away. "
                "If you feel very unwell, please call 995 or ask someone nearby for help immediately."
            )
        else:
            response = (
                "我注意到您的情况，请先保持冷静 🙏 "
                "我已立即通知您的健康监护系统进行评估。"
                "如果感到非常不适，请立刻拨打 995 或告诉身边的人。"
            )
    else:
        if language == "English":
            response = (
                "I've flagged this for your health monitoring system to review. "
                "Please monitor how you feel and contact your doctor if it gets worse."
            )
        else:
            response = (
                "我已将您的情况记录并通知健康监护系统评估。"
                "请继续观察您的状态，如有加重请及时联系您的医生。"
            )

    # 构建预警触发信号 → Julia 模块
    alert_trigger = {
        "user_id":            state["user_id"],
        "timestamp":          datetime.now().isoformat(),
        "alert_input":        state["user_input"],
        "emotion_label":      emotion_label,
        "emotion_confidence": state.get("emotion_confidence", 0.0),
        "severity":           "待评估",
        "source":             "用户自报",
    }

    print(f"\n助手：{response}")
    print(f"[预警转发] alert_trigger 已生成 → 等待 Julia 模块接收")
    return {"response": response, "alert_trigger": alert_trigger}
