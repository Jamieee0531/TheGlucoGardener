"""
对话历史 + 用户档案管理
短期记忆：近N轮对话（存在内存/State里）
长期记忆：用户档案（实际项目接数据库，现在用字典模拟）
"""
from chatbot.config.settings import MAX_HISTORY_TURNS, MAX_HISTORY_CHARS


# ============================================================
# 短期记忆：对话历史
# ============================================================

def add_to_history(history: list, role: str, content: str) -> list:
    """
    添加一条消息到对话历史
    role: "user" 或 "assistant"
    """
    history = history.copy()
    history.append({"role": role, "content": content})

    # 超出轮数限制，裁剪最旧的（保留偶数条，维持user/assistant对称）
    max_messages = MAX_HISTORY_TURNS * 2
    if len(history) > max_messages:
        history = history[-max_messages:]

    return history


def format_history_for_llm(history: list) -> list:
    """
    把历史记录转换为 LangChain Message 格式
    供 Agent 的 prompt 使用
    """
    from langchain_core.messages import HumanMessage, AIMessage
    messages = []
    for item in history:
        if item["role"] == "user":
            messages.append(HumanMessage(content=item["content"]))
        else:
            messages.append(AIMessage(content=item["content"]))
    return messages


# ============================================================
# 长期记忆：用户档案
# 实际项目中替换为数据库查询
# ============================================================

# 模拟用户数据库
_USER_PROFILES = {
    "user_001": {
        "name": "陈先生",
        "language": "Chinese",
        "conditions": ["Type 2 Diabetes", "高血压"],
        "medications": ["Metformin 500mg", "Amlodipine 5mg"],
        "preferences": {
            "reminder_time": "08:00",
            "diet": "低碳水",
        }
    },
    "user_002": {
        "name": "Mr Tan",
        "language": "English",
        "conditions": ["Type 2 Diabetes"],
        "medications": ["Metformin 1000mg"],
        "preferences": {
            "reminder_time": "09:00",
            "diet": "halal",
        }
    },
}

_DEFAULT_PROFILE = {
    "name": "患者",
    "language": "Chinese",
    "conditions": ["Type 2 Diabetes"],
    "medications": [],
    "preferences": {},
}


def get_user_profile(user_id: str) -> dict:
    """从 PostgreSQL users 表读取用户档案，失败降级 mock。"""
    try:
        from chatbot.db.connection import db_cursor
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT name, language, conditions, medications, preferences
                FROM users WHERE user_id = %s
                """,
                (user_id,),
            )
            row = cur.fetchone()
        if row:
            return {
                "name":        row["name"] or "患者",
                "language":    row["language"] or "Chinese",
                "conditions":  list(row["conditions"] or []),
                "medications": list(row["medications"] or []),
                "preferences": dict(row["preferences"] or {}),
            }
    except Exception as e:
        print(f"[Memory] 用户档案 DB 失败（{e}），使用 mock")
    return _USER_PROFILES.get(user_id, _DEFAULT_PROFILE.copy())


def update_user_profile(user_id: str, updates: dict) -> dict:
    """更新用户档案（写 PostgreSQL，失败降级 in-memory）。"""
    try:
        from chatbot.db.connection import db_cursor
        allowed = {"name", "language", "conditions", "medications", "preferences"}
        fields = {k: v for k, v in updates.items() if k in allowed}
        if fields:
            import json
            set_clauses = []
            values = []
            for k, v in fields.items():
                set_clauses.append(f"{k} = %s")
                values.append(json.dumps(v) if isinstance(v, (dict, list)) else v)
            values.append(user_id)
            with db_cursor(commit=True) as cur:
                cur.execute(
                    f"UPDATE users SET {', '.join(set_clauses)} WHERE user_id = %s",
                    values,
                )
    except Exception as e:
        print(f"[Memory] 用户档案更新 DB 失败（{e}），仅更新 in-memory")
        profile = _USER_PROFILES.get(user_id, _DEFAULT_PROFILE.copy())
        profile.update(updates)
        _USER_PROFILES[user_id] = profile
    return get_user_profile(user_id)
