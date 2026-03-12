"""
不调LLM
生成 task_trigger 字典 + 给用户一个即时回复
等task模块接收
"""
from datetime import datetime
from chatbot.state.chat_state import ChatState


def task_forward_node(state: ChatState) -> dict:
    """
    任务转发 Agent：
    - 不需要 LLM，直接构建触发信号
    - 给用户简短确认回复
    - 发出 task_trigger → Chayi 模块处理
    """
    profile  = state.get("user_profile", {})
    language = profile.get("language", "Chinese")

    user_input = state["user_input"]

    # 根据具体请求给出不同回复
    if any(k in user_input for k in ["积分", "points", "score"]):
        response = "好的，我帮您查询积分，稍等一下！任务系统会把结果告诉您 😊" if language != "English" else "Sure, let me check your points! The task system will get back to you shortly 😊"
    elif any(k in user_input for k in ["提醒", "reminder", "设置", "set"]):
        response = "好的，提醒已设置！到时间我会通知您的 ⏰" if language != "English" else "Done! I've set up the reminder for you ⏰"
    elif any(k in user_input for k in ["照片", "photo", "上传", "upload"]):
        response = "收到！请上传您的餐食照片，我会帮您记录 📷" if language != "English" else "Got it! Please upload your meal photo and I'll log it for you 📷"
    elif any(k in user_input for k in ["步", "steps", "走", "打卡"]):
        response = "太棒了！步数已记录，继续保持运动习惯 💪" if language != "English" else "Great job! Your steps have been logged. Keep it up 💪"
    else:
        response = "好的，我已经帮您记录了！任务系统会为您安排 😊" if language != "English" else "Got it! The task system will take care of it for you 😊"

    # 构建触发信号，传给 Chayi 的任务发布模块
    task_trigger = {
        "user_id":   state["user_id"],
        "timestamp": datetime.now().isoformat(),
        "request":   state["user_input"],
        "type":      "task_request",
        "intent":    "task",
    }

    print(f"\n助手：{response}")
    print(f"[任务转发] task_trigger 已生成 → 等待 Chayi 模块接收")
    return {"response": response, "task_trigger": task_trigger}
