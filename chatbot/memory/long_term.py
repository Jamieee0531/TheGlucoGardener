"""
长期记忆：情绪相关数据（SQLite）
- emotion_log: 最新语音情绪（每用户一行）
- daily_emotion_log: 每日非 neutral 情绪记录
- health_events: 保留用于读取旧 emotion_summary 数据
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
            # 语音情绪日志：每用户一行，覆盖写入（仅语音模式，confidence >= 0.6）
            conn.execute("""
                CREATE TABLE IF NOT EXISTS emotion_log (
                    user_id       TEXT PRIMARY KEY,
                    emotion_label TEXT NOT NULL,
                    recorded_at   TEXT NOT NULL
                )
            """)
            # 每日情绪日志：每次非 neutral 情绪记录一条
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_emotion_log (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id       TEXT NOT NULL,
                    emotion_label TEXT NOT NULL,
                    user_input    TEXT NOT NULL,
                    timestamp     TEXT NOT NULL
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_daily_emotion_user "
                "ON daily_emotion_log(user_id, timestamp)"
            )

    def upsert_emotion_log(self, user_id: str, emotion_label: str) -> None:
        """覆盖写入最新语音情绪（每用户一行）。调用前已过滤 confidence < 0.6。"""
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.execute(
                "INSERT INTO emotion_log (user_id, emotion_label, recorded_at) "
                "VALUES (?, ?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET "
                "emotion_label=excluded.emotion_label, recorded_at=excluded.recorded_at",
                (user_id, emotion_label, datetime.now().isoformat()),
            )

    def get_emotion_summaries(self, user_id: str, days: int = 14) -> list:
        """获取近 N 天情绪摘要，按时间倒序最多 5 条。"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        with sqlite3.connect(str(DB_PATH)) as conn:
            rows = conn.execute(
                "SELECT content, timestamp FROM health_events "
                "WHERE user_id=? AND event_type='emotion_summary' AND timestamp>? "
                "ORDER BY timestamp DESC LIMIT 5",
                (user_id, cutoff),
            ).fetchall()
        return [
            {"text": json.loads(r[0]).get("text", ""), "timestamp": r[1]}
            for r in rows
        ]

    def format_emotion_summary_for_llm(self, user_id: str, days: int = 14) -> str:
        """将近期情绪摘要格式化为叙事段落注入 companion prompt。"""
        summaries = self.get_emotion_summaries(user_id, days)
        if not summaries:
            return ""
        lines = ["【患者近期情绪背景】"]
        for s in summaries:
            ts = s["timestamp"][:10]
            lines.append(f"- {ts}：{s['text']}")
        return "\n".join(lines)

    # ── daily_emotion_log methods ──────────────────────────────────

    def log_daily_emotion(self, user_id: str, emotion_label: str, user_input: str) -> None:
        """Log a non-neutral emotion + input for daily summary."""
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.execute(
                "INSERT INTO daily_emotion_log "
                "(user_id, emotion_label, user_input, timestamp) VALUES (?, ?, ?, ?)",
                (user_id, emotion_label, user_input, datetime.now().isoformat()),
            )

    def get_daily_emotions(self, user_id: str) -> list:
        """Get today's emotion log entries."""
        today = datetime.now().strftime("%Y-%m-%d")
        with sqlite3.connect(str(DB_PATH)) as conn:
            rows = conn.execute(
                "SELECT emotion_label, user_input, timestamp FROM daily_emotion_log "
                "WHERE user_id=? AND timestamp LIKE ? ORDER BY timestamp",
                (user_id, f"{today}%"),
            ).fetchall()
        return [
            {"emotion_label": r[0], "user_input": r[1], "timestamp": r[2]}
            for r in rows
        ]

    def clear_daily_emotions(self, user_id: str) -> None:
        """Clear today's emotion log (called after 23:59 summary)."""
        today = datetime.now().strftime("%Y-%m-%d")
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.execute(
                "DELETE FROM daily_emotion_log WHERE user_id=? AND timestamp LIKE ?",
                (user_id, f"{today}%"),
            )


# ── 单例 ─────────────────────────────────────────────────────────
_store: "HealthEventStore | None" = None


def get_health_store() -> HealthEventStore:
    global _store
    if _store is None:
        _store = HealthEventStore()
    return _store
