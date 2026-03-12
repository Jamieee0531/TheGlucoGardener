"""
长期记忆：用户健康事件日志（SQLite）
存储每轮 expert agent 确认的血糖/饮食/用药数据
expert agent 每次启动前读取近 N 天记录注入 prompt
"""
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "health_events.db"


class HealthEventStore:
    def __init__(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS health_events (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id    TEXT    NOT NULL,
                    event_type TEXT    NOT NULL,
                    content    TEXT    NOT NULL,
                    timestamp  TEXT    NOT NULL
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_user_ts "
                "ON health_events(user_id, timestamp)"
            )

    def log_event(self, user_id: str, event_type: str, content: dict) -> None:
        """记录一条健康事件。event_type: 'glucose' | 'diet' | 'medication'"""
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.execute(
                "INSERT INTO health_events "
                "(user_id, event_type, content, timestamp) VALUES (?, ?, ?, ?)",
                (user_id, event_type,
                 json.dumps(content, ensure_ascii=False),
                 datetime.now().isoformat()),
            )

    def get_recent(self, user_id: str, days: int = 7) -> list:
        """获取近 N 天健康事件，按时间倒序最多 20 条。"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        with sqlite3.connect(str(DB_PATH)) as conn:
            rows = conn.execute(
                "SELECT event_type, content, timestamp FROM health_events "
                "WHERE user_id=? AND timestamp>? ORDER BY timestamp DESC LIMIT 20",
                (user_id, cutoff),
            ).fetchall()
        return [
            {"type": r[0], "content": json.loads(r[1]), "timestamp": r[2]}
            for r in rows
        ]

    def format_for_llm(self, user_id: str, days: int = 7) -> str:
        """将近期健康记录格式化为 LLM 可读的上下文字符串。"""
        events = self.get_recent(user_id, days)
        if not events:
            return ""
        _label = {"glucose": "血糖", "diet": "饮食", "medication": "用药"}
        lines = [f"【患者过去 {days} 天健康记录】"]
        for e in events[:10]:
            date  = e["timestamp"][:10]
            val   = e["content"].get("value", "?")
            label = _label.get(e["type"], e["type"])
            lines.append(f"- {date} {label}：{val}")
        return "\n".join(lines)


# ── 单例 ─────────────────────────────────────────────────────────
_store: "HealthEventStore | None" = None


def get_health_store() -> HealthEventStore:
    global _store
    if _store is None:
        _store = HealthEventStore()
    return _store
