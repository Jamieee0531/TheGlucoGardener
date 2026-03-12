"""
state/chat_state.py
LangGraph 共享状态定义
"""
from typing import TypedDict, Literal, Optional


class ChatState(TypedDict):
    # ── 输入 ─────────────────────────────────────────────
    user_input:         str
    input_mode:         Literal["text", "voice"]
    chat_mode:          Literal["personal", "group"]
    user_id:            str

    audio_path:          Optional[str]    # 语音输入时的音频文件路径

    # ── MERaLiON 输出 ────────────────────────────────────
    transcribed_text:   Optional[str]
    emotion_label:      Optional[str]
    emotion_confidence: Optional[float]

    # ── Triage 路由结果 ──────────────────────────────────
    intent:             Optional[str]
    all_intents:        Optional[list]

    # ── Policy 层输出 ────────────────────────────────────
    policy_instruction: Optional[str]   # 策略指令字符串
    recent_emotions:    Optional[list]  # 最近5轮情绪记录
    persistent_alert:   Optional[dict]  # 持续负面情绪预警

    # ── 对话记忆 ─────────────────────────────────────────
    history:            list
    user_profile:       dict

    # ── 设备数据（血糖仪/药盒，每轮对话由 device_sync_node 注入）──
    device_data:        Optional[dict]   # {"glucose": [...], "medication": {...}}

    # ── Agent 输出 ────────────────────────────────────────
    response:           Optional[str]

    # ── 下游触发 ─────────────────────────────────────────
    emotion_log:        Optional[dict]
    task_trigger:       Optional[dict]
    alert_trigger:      Optional[dict]

    # ── 图片 / Vision Agent ────────────────────────────────
    image_paths:        Optional[list]    # 用户发送的图片路径列表
    vision_result:      Optional[list]    # Vision Agent 识别结果列表
