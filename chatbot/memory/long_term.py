"""
长期记忆：全部写入华为云 PostgreSQL
表对应关系（schema.sql）：
  - user_emotion_log     每轮对话情绪流水
  - user_emotion_summary 每日情绪汇总（23:59 定时任务生成）
  - user_facts           结构化用户事实（可增删，支持过期）
  - user_context         用户背景文本（health_context / current_focus / long_term_bg）
"""
from __future__ import annotations

from datetime import datetime, timedelta
from chatbot.db.connection import db_cursor


class HealthEventStore:

    # ── emotion_log ────────────────────────────────────────────────

    def log_emotion(self, user_id: str, emotion_label: str, user_input: str) -> None:
        """每轮对话写入一条情绪记录。"""
        with db_cursor(commit=True) as cur:
            cur.execute(
                """
                INSERT INTO user_emotion_log (user_id, user_input, emotion_label, source, recorded_at)
                VALUES (%s, %s, %s, %s, NOW())
                """,
                (user_id, user_input, emotion_label, "openai"),
            )

    def get_today_emotions(self, user_id: str) -> list:
        """获取今日所有情绪记录（供 23:59 汇总用）。"""
        today = datetime.now().strftime("%Y-%m-%d")
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT emotion_label, user_input, recorded_at
                FROM user_emotion_log
                WHERE user_id = %s
                  AND recorded_at >= %s::date
                  AND recorded_at <  %s::date + INTERVAL '1 day'
                ORDER BY recorded_at
                """,
                (user_id, today, today),
            )
            rows = cur.fetchall()
        return [
            {
                "emotion_label": r["emotion_label"],
                "user_input":    r["user_input"],
                "recorded_at":   str(r["recorded_at"]),
            }
            for r in rows
        ]

    def get_today_emotion_user_ids(self) -> list:
        """获取今日有情绪记录的所有 user_id。"""
        today = datetime.now().strftime("%Y-%m-%d")
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT user_id FROM user_emotion_log
                WHERE recorded_at >= %s::date
                  AND recorded_at <  %s::date + INTERVAL '1 day'
                """,
                (today, today),
            )
            rows = cur.fetchall()
        return [r["user_id"] for r in rows]

    # ── emotion_summary ────────────────────────────────────────────

    def save_emotion_summary(self, user_id: str, text: str, date: str) -> None:
        """写入每日情绪汇总（由 23:59 定时任务调用）。UPSERT 防重复。"""
        with db_cursor(commit=True) as cur:
            cur.execute(
                """
                INSERT INTO user_emotion_summary (user_id, summary_date, summary_text)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, summary_date)
                DO UPDATE SET summary_text = EXCLUDED.summary_text
                """,
                (user_id, date, text),
            )

    def get_emotion_summaries(self, user_id: str, days: int = 14) -> list:
        """获取近 N 天情绪摘要，按日期倒序最多 5 条。"""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT summary_text AS text, summary_date::text AS date
                FROM user_emotion_summary
                WHERE user_id = %s AND summary_date >= %s
                ORDER BY summary_date DESC
                LIMIT 5
                """,
                (user_id, cutoff),
            )
            rows = cur.fetchall()
        return [{"text": r["text"], "date": r["date"]} for r in rows]

    # ── user_facts ─────────────────────────────────────────────────

    def get_active_facts(self, user_id: str) -> list:
        """获取未过期的用户事实列表（供测试和 format_memory_for_prompt 使用）。"""
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT category, content, confidence, created_at
                FROM user_facts
                WHERE user_id = %s
                  AND (expires_at IS NULL OR expires_at > NOW())
                ORDER BY created_at DESC
                LIMIT 20
                """,
                (user_id,),
            )
            rows = cur.fetchall()
        return [
            {
                "category":   r["category"],
                "content":    r["content"],
                "confidence": float(r["confidence"]) if r["confidence"] is not None else 1.0,
            }
            for r in rows
        ]

    def upsert_fact(self, user_id: str, category: str, content: str,
                    confidence: float, expires_in_days: int = None) -> None:
        """写入或更新一条用户事实（按 user_id + content 去重，无 unique constraint 版）。"""
        from datetime import timedelta
        expires_at = (
            datetime.now() + timedelta(days=expires_in_days)
            if expires_in_days else None
        )
        with db_cursor(commit=True) as cur:
            # Update existing row if content matches, else insert
            cur.execute(
                """
                UPDATE user_facts
                SET category = %s, confidence = %s, expires_at = %s, created_at = NOW()
                WHERE user_id = %s AND content = %s
                """,
                (category, confidence, expires_at, user_id, content),
            )
            if cur.rowcount == 0:
                cur.execute(
                    """
                    INSERT INTO user_facts (user_id, category, content, confidence, expires_at)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (user_id, category, content, confidence, expires_at),
                )

    # ── user_context ────────────────────────────────────────────────

    def get_user_context(self, user_id: str) -> dict:
        """获取用户背景文本（health_context / current_focus / long_term_bg）。"""
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT health_context, current_focus, long_term_bg
                FROM user_context
                WHERE user_id = %s
                """,
                (user_id,),
            )
            row = cur.fetchone()
        if row is None:
            return {"health_context": None, "current_focus": None, "long_term_bg": None}
        return {
            "health_context": row.get("health_context"),
            "current_focus":  row.get("current_focus"),
            "long_term_bg":   row.get("long_term_bg"),
        }

    def upsert_context(self, user_id: str, health_context: str = None,
                       current_focus: str = None, long_term_bg: str = None) -> None:
        """写入或更新用户背景文本（UPSERT，只更新非 None 字段）。"""
        with db_cursor(commit=True) as cur:
            cur.execute(
                """
                INSERT INTO user_context (user_id, health_context, current_focus, long_term_bg)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    health_context = COALESCE(EXCLUDED.health_context, user_context.health_context),
                    current_focus  = COALESCE(EXCLUDED.current_focus,  user_context.current_focus),
                    long_term_bg   = COALESCE(EXCLUDED.long_term_bg,   user_context.long_term_bg),
                    updated_at     = NOW()
                """,
                (user_id, health_context, current_focus, long_term_bg),
            )

    def format_emotion_summary_for_llm(self, user_id: str, days: int = 14) -> str:
        """将近期情绪摘要格式化为叙事段落注入 prompt。"""
        summaries = self.get_emotion_summaries(user_id, days)
        if not summaries:
            return ""
        lines = ["【患者近期情绪背景】"]
        for s in summaries:
            lines.append(f"- {s['date']}：{s['text']}")
        return "\n".join(lines)

    # ── format_memory_for_prompt ───────────────────────────────────

    def format_memory_for_prompt(self, user_id: str, days: int = 14) -> str:
        """
        组合三层长期记忆供 Agent prompt 使用：
        1. 情绪摘要（user_emotion_summary）
        2. 用户已知事实（user_facts）
        3. 用户背景文本（user_context）
        任一层获取失败均降级，不影响其他层。
        """
        parts = []

        # ── 1. 情绪摘要 ───────────────────────────────────────────
        try:
            emotion_block = self.format_emotion_summary_for_llm(user_id, days)
            if emotion_block:
                parts.append(emotion_block)
        except Exception as e:
            print(f"[Memory] 情绪摘要读取失败（{e}）")

        # ── 2. user_facts ─────────────────────────────────────────
        try:
            with db_cursor() as cur:
                cur.execute(
                    """
                    SELECT content, category FROM user_facts
                    WHERE user_id = %s
                      AND (expires_at IS NULL OR expires_at > NOW())
                    ORDER BY created_at DESC
                    LIMIT 20
                    """,
                    (user_id,),
                )
                facts = cur.fetchall()
            if facts:
                fact_lines = ["【用户已知信息】"]
                for row in facts:
                    fact_lines.append(f"- [{row['category']}] {row['content']}")
                parts.append("\n".join(fact_lines))
        except Exception as e:
            print(f"[Memory] user_facts 读取失败（{e}）")

        # ── 3. user_context ───────────────────────────────────────
        try:
            with db_cursor() as cur:
                cur.execute(
                    """
                    SELECT health_context, current_focus, long_term_bg
                    FROM user_context
                    WHERE user_id = %s
                    """,
                    (user_id,),
                )
                ctx = cur.fetchone()
            if ctx:
                ctx_lines = []
                if ctx.get("health_context"):
                    ctx_lines.append(f"【生活背景】{ctx['health_context']}")
                if ctx.get("current_focus"):
                    ctx_lines.append(f"【近期关注】{ctx['current_focus']}")
                if ctx.get("long_term_bg"):
                    ctx_lines.append(f"【长期背景】{ctx['long_term_bg']}")
                if ctx_lines:
                    parts.append("\n".join(ctx_lines))
        except Exception as e:
            print(f"[Memory] user_context 读取失败（{e}）")

        return "\n\n".join(parts)


# ── 单例 ──────────────────────────────────────────────────────────
_store: "HealthEventStore | None" = None


def get_health_store() -> HealthEventStore:
    global _store
    if _store is None:
        _store = HealthEventStore()
    return _store
