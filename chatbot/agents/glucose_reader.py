"""
glucose_reader — 读取共享数据库最近 1 小时血糖（最多 6 条 raw value）
生产环境：替换 _MOCK_CGM_DATA 为真实数据库查询
"""
from chatbot.state.chat_state import ChatState

# ── Mock data（生产环境替换为 SELECT * FROM user_cgm_log WHERE ...）──
_MOCK_CGM_DATA = {
    "user_001": [
        {"recorded_at": "2026-03-14T14:00:00", "glucose": 6.8},
        {"recorded_at": "2026-03-14T14:10:00", "glucose": 7.2},
        {"recorded_at": "2026-03-14T14:20:00", "glucose": 8.5},
    ],
    "user_002": [
        {"recorded_at": "2026-03-14T14:00:00", "glucose": 7.1},
        {"recorded_at": "2026-03-14T14:10:00", "glucose": 10.3},
    ],
}


_MOCK_WEEKLY_GLUCOSE = {
    "user_001": [
        {"date": "2026-03-08", "avg": 7.4, "min": 5.9, "max": 9.8},
        {"date": "2026-03-09", "avg": 6.9, "min": 5.6, "max": 8.7},
        {"date": "2026-03-10", "avg": 8.1, "min": 6.2, "max": 11.3},
        {"date": "2026-03-11", "avg": 7.6, "min": 6.0, "max": 9.5},
        {"date": "2026-03-12", "avg": 7.0, "min": 5.8, "max": 8.9},
        {"date": "2026-03-13", "avg": 7.8, "min": 6.1, "max": 10.2},
        {"date": "2026-03-14", "avg": 7.5, "min": 6.8, "max": 8.5},
    ],
    "user_002": [
        {"date": "2026-03-08", "avg": 8.2, "min": 6.5, "max": 12.1},
        {"date": "2026-03-09", "avg": 7.9, "min": 6.3, "max": 10.5},
        {"date": "2026-03-10", "avg": 9.1, "min": 7.0, "max": 13.2},
        {"date": "2026-03-11", "avg": 8.5, "min": 6.8, "max": 11.4},
        {"date": "2026-03-12", "avg": 7.7, "min": 6.2, "max": 10.8},
        {"date": "2026-03-13", "avg": 8.3, "min": 6.9, "max": 11.6},
        {"date": "2026-03-14", "avg": 8.7, "min": 7.1, "max": 10.3},
    ],
}

_MOCK_WEEKLY_DIET: dict = {}


def glucose_reader_node(state: ChatState) -> dict:
    """读取近 1 小时血糖（最多 6 条），优先查 PostgreSQL，失败降级 mock。"""
    user_id = state["user_id"]
    try:
        from chatbot.db.connection import db_cursor
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT recorded_at::text AS recorded_at, glucose
                FROM user_cgm_log
                WHERE user_id = %s
                  AND recorded_at >= NOW() - INTERVAL '1 hour'
                ORDER BY recorded_at DESC
                LIMIT 6
                """,
                (user_id,),
            )
            rows = cur.fetchall()
        readings = [{"recorded_at": r["recorded_at"], "glucose": float(r["glucose"])} for r in rows]
        print(f"[GlucoseReader] PostgreSQL: {len(readings)} 条")
    except Exception as e:
        print(f"[GlucoseReader] DB 失败（{e}），使用 mock 数据")
        readings = _MOCK_CGM_DATA.get(user_id, [])[-6:]
    return {"glucose_readings": readings}


def get_weekly_glucose_summary(user_id: str) -> list:
    """近 7 天每日血糖统计，优先查 PostgreSQL user_glucose_daily_stats。"""
    try:
        from chatbot.db.connection import db_cursor
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT stat_date::text AS date,
                       avg_glucose    AS avg,
                       nadir_glucose  AS min,
                       peak_glucose   AS max
                FROM user_glucose_daily_stats
                WHERE user_id = %s
                  AND stat_date >= CURRENT_DATE - INTERVAL '7 days'
                ORDER BY stat_date
                """,
                (user_id,),
            )
            rows = cur.fetchall()
        return [{"date": r["date"], "avg": float(r["avg"]),
                 "min": float(r["min"]), "max": float(r["max"])} for r in rows]
    except Exception as e:
        print(f"[GlucoseReader] 周统计 DB 失败（{e}），使用 mock")
        return _MOCK_WEEKLY_GLUCOSE.get(user_id, [])


def get_weekly_diet_history(user_id: str) -> list:
    """近 7 天饮食历史，优先查 PostgreSQL user_food_log。"""
    try:
        from chatbot.db.connection import db_cursor
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT recorded_at::date::text AS date,
                       STRING_AGG(food_name, '；' ORDER BY recorded_at) AS meals
                FROM user_food_log
                WHERE user_id = %s
                  AND recorded_at >= CURRENT_DATE - INTERVAL '7 days'
                GROUP BY recorded_at::date
                ORDER BY recorded_at::date
                """,
                (user_id,),
            )
            rows = cur.fetchall()
        return [{"date": r["date"], "meals": r["meals"]} for r in rows]
    except Exception as e:
        print(f"[GlucoseReader] 饮食历史 DB 失败（{e}），使用 mock")
        return _MOCK_WEEKLY_DIET.get(user_id, [])
