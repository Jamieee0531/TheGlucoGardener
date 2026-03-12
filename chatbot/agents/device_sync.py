"""
device_sync_node
模拟从血糖仪 / 智能药盒 / 医院系统 API 读取当日数据
生产环境替换为真实外部 API 调用，接口不变
"""
from chatbot.state.chat_state import ChatState


# ── 模拟设备数据库 ─────────────────────────────────────────────
_MOCK_DEVICE_DATA = {
    "user_001": {
        "glucose": [
            {"time": "07:30", "value": 6.8},
            {"time": "11:00", "value": 9.2},
            {"time": "14:30", "value": 8.5},
        ],
        "medication": {
            "Metformin 500mg": True,
            "Amlodipine 5mg":  True,
        },
    },
    "user_002": {
        "glucose": [
            {"time": "08:00", "value": 7.1},
            {"time": "13:00", "value": 10.3},
        ],
        "medication": {
            "Metformin 1000mg": False,   # 今日漏服，演示用
        },
    },
}

_DEFAULT_DEVICE_DATA: dict = {
    "glucose":    [{"time": "08:00", "value": 7.0}],
    "medication": {},
}


def device_sync_node(state: ChatState) -> dict:
    """
    读取当日设备数据，注入 State。
    生产环境：替换 _MOCK_DEVICE_DATA 查询为真实 API。
    """
    user_id = state["user_id"]
    data    = _MOCK_DEVICE_DATA.get(user_id, _DEFAULT_DEVICE_DATA)

    glucose_count = len(data.get("glucose", []))
    med_status    = {k: ("✅" if v else "❌") for k, v in data.get("medication", {}).items()}
    print(f"[DeviceSync] 血糖 {glucose_count} 条 | 用药 {med_status}")

    return {"device_data": data}
