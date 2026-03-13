"""
glucose_reader — 读取共享数据库最近 1 小时血糖（最多 6 条 raw value）
生产环境：替换 _MOCK_CGM_DATA 为真实数据库查询
"""
from chatbot.state.chat_state import ChatState

# ── Mock data（生产环境替换为 SELECT * FROM user_cgm_log WHERE ...）──
_MOCK_CGM_DATA = {
    "user_001": [
        {"recorded_at": "2026-03-13T14:00:00", "glucose": 6.8},
        {"recorded_at": "2026-03-13T14:10:00", "glucose": 7.2},
        {"recorded_at": "2026-03-13T14:20:00", "glucose": 8.5},
    ],
    "user_002": [
        {"recorded_at": "2026-03-13T14:00:00", "glucose": 7.1},
        {"recorded_at": "2026-03-13T14:10:00", "glucose": 10.3},
    ],
}


def glucose_reader_node(state: ChatState) -> dict:
    """读取最近 1 小时血糖数据（最多 6 条），注入 state。只读，不写。"""
    user_id = state["user_id"]
    readings = _MOCK_CGM_DATA.get(user_id, [])
    # 最多 6 条
    readings = readings[-6:]
    print(f"[GlucoseReader] {len(readings)} 条血糖数据")
    return {"glucose_readings": readings}
