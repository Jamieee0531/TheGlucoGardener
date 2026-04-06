"""
chatbot/db/seed.py
写入四个 Demo 用户的完整测试数据，直接操作 PostgreSQL（psycopg2）。

生成内容：
  - users                 用户档案
  - user_weekly_patterns  每周运动计划
  - user_known_places     已知地点
  - user_emergency_contacts 紧急联系人
  - user_cgm_log          过去 7 天血糖（10 分钟一条）
  - user_hr_log           过去 7 天心率 + GPS
  - user_exercise_log     过去 7 天运动记录
  - reward_log            积分初始化
  - user_emotion_summary  近 3 天情绪摘要（供陪伴 Agent 测试）
  - user_glucose_daily_stats 近 7 天每日统计

Usage:
  cd TheGlucoGardener
  python -m chatbot.db.seed
"""
from __future__ import annotations

import json
import math
import os
import random
import sys
from datetime import date, datetime, time, timedelta

# 确保项目根目录在 path 里
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
load_dotenv()

from chatbot.db.connection import db_cursor

random.seed(42)   # 可复现

# ─────────────────────────────────────────────────────────────────
# Demo 用户定义
# ─────────────────────────────────────────────────────────────────

USERS = [
    {
        "user_id":    "demo_en",
        "name":       "Mr Tan",
        "birth_year": 1968,
        "gender":     "male",
        "waist_cm":   92.0,
        "weight_kg":  78.0,
        "height_cm":  170.0,
        "language":   "English",
        "conditions": ["Type 2 Diabetes"],
        "medications": ["Metformin 1000mg"],
        "preferences": {"diet": "halal"},
        "avatar": "avatar_2",
        # 每周运动：Mon/Wed/Fri 早上跑步
        "patterns": [
            {"day_of_week": 0, "start": time(7, 0),  "end": time(7, 45),  "type": "cardio"},
            {"day_of_week": 2, "start": time(7, 0),  "end": time(7, 45),  "type": "cardio"},
            {"day_of_week": 4, "start": time(7, 0),  "end": time(7, 45),  "type": "cardio"},
        ],
        "places": [
            ("Home",   "home",   1.3800, 103.7650),
            ("Clinic", "office", 1.3600, 103.7500),
        ],
        "contacts": [
            ("Mary Tan",   "+6591234001", "family",  ["hard_low_glucose", "data_gap"]),
            ("Dr Ahmad",   "+6562345678", "doctor",  ["hard_low_glucose", "hard_high_hr"]),
        ],
        "emotion_summaries": [
            (date.today() - timedelta(days=2), "Feeling anxious about upcoming HbA1c test.",   "fearful"),
            (date.today() - timedelta(days=1), "More relaxed after a good walk in the morning.","neutral"),
        ],
        # 血糖偏高（控制不佳）
        "glucose_profile": {"baseline": 6.8, "meal_spike": 3.2, "sd": 0.5},
    },
    {
        "user_id":    "demo_zh",
        "name":       "陈先生",
        "birth_year": 1962,
        "gender":     "male",
        "waist_cm":   95.0,
        "weight_kg":  82.0,
        "height_cm":  168.0,
        "language":   "Chinese",
        "conditions": ["Type 2 Diabetes", "高血压"],
        "medications": ["Metformin 500mg", "Amlodipine 5mg"],
        "preferences": {"diet": "低碳水"},
        "avatar": "avatar_1",
        "patterns": [
            {"day_of_week": 1, "start": time(18, 0), "end": time(19, 0), "type": "cardio"},
            {"day_of_week": 4, "start": time(18, 0), "end": time(19, 0), "type": "cardio"},
            {"day_of_week": 6, "start": time(8, 0),  "end": time(9, 0),  "type": "cardio"},
        ],
        "places": [
            ("家",     "home",   1.3521, 103.8198),
            ("公园",   "gym",    1.3600, 103.8300),
            ("诊所",   "office", 1.3400, 103.8100),
        ],
        "contacts": [
            ("陈太太",  "+6591234002", "family", ["hard_low_glucose", "hard_high_hr", "data_gap"]),
        ],
        "emotion_summaries": [
            (date.today() - timedelta(days=3), "子女在国外，感到孤独，情绪低落。",              "sad"),
            (date.today() - timedelta(days=1), "散步后心情好转，主动问起了饮食建议。",          "neutral"),
        ],
        # 血糖较稳定（控制良好）
        "glucose_profile": {"baseline": 5.8, "meal_spike": 2.0, "sd": 0.4},
    },
    {
        "user_id":    "demo_ms",
        "name":       "Encik Ahmad",
        "birth_year": 1975,
        "gender":     "male",
        "waist_cm":   88.0,
        "weight_kg":  80.0,
        "height_cm":  172.0,
        "language":   "Malay",
        "conditions": ["Type 2 Diabetes"],
        "medications": ["Metformin 500mg"],
        "preferences": {"diet": "halal"},
        "avatar": "avatar_3",
        "patterns": [
            {"day_of_week": 0, "start": time(6, 30), "end": time(7, 30), "type": "resistance_training"},
            {"day_of_week": 3, "start": time(6, 30), "end": time(7, 30), "type": "resistance_training"},
            {"day_of_week": 5, "start": time(8, 0),  "end": time(9, 0),  "type": "cardio"},
        ],
        "places": [
            ("Rumah",  "home",   1.4200, 103.8400),
            ("Gym",    "gym",    1.4100, 103.8500),
        ],
        "contacts": [
            ("Siti Ahmad", "+6591234003", "family", ["hard_low_glucose", "data_gap"]),
        ],
        "emotion_summaries": [
            (date.today() - timedelta(days=2), "Bimbang tentang puasa Ramadan dan kawalan gula darah.", "fearful"),
            (date.today() - timedelta(days=1), "Lebih tenang setelah berbual dengan doktor.",           "neutral"),
        ],
        "glucose_profile": {"baseline": 6.2, "meal_spike": 2.5, "sd": 0.45},
    },
    {
        "user_id":    "demo_ta",
        "name":       "Mr Kumar",
        "birth_year": 1970,
        "gender":     "male",
        "waist_cm":   90.0,
        "weight_kg":  75.0,
        "height_cm":  165.0,
        "language":   "Tamil",
        "conditions": ["Type 2 Diabetes"],
        "medications": ["Metformin 500mg"],
        "preferences": {},
        "avatar": "avatar_4",
        "patterns": [
            {"day_of_week": 2, "start": time(17, 30), "end": time(18, 30), "type": "cardio"},
            {"day_of_week": 5, "start": time(7, 0),   "end": time(8, 0),   "type": "cardio"},
        ],
        "places": [
            ("Home",   "home",   1.3100, 103.8600),
        ],
        "contacts": [
            ("Priya Kumar", "+6591234004", "family", ["hard_low_glucose", "hard_high_hr"]),
        ],
        "emotion_summaries": [
            (date.today() - timedelta(days=1), "Stressed about work and managing diabetes simultaneously.", "sad"),
        ],
        "glucose_profile": {"baseline": 6.5, "meal_spike": 2.8, "sd": 0.5},
    },
]


# ─────────────────────────────────────────────────────────────────
# 血糖生成（仿 CGM 曲线）
# ─────────────────────────────────────────────────────────────────

def _glucose_at(ts: datetime, profile: dict) -> float:
    """根据时间点模拟血糖值（餐后高峰 + 基础波动）。"""
    h = ts.hour + ts.minute / 60.0
    base = profile["baseline"]
    spike = profile["meal_spike"]
    sd = profile["sd"]

    # 早餐 7:00–9:00，午餐 12:00–14:00，晚餐 18:00–20:00
    meal_bump = 0.0
    for meal_h in (7.5, 13.0, 19.0):
        dt = h - meal_h
        if -0.5 <= dt <= 2.5:   # 餐后 2.5 小时内有高峰
            meal_bump += spike * math.exp(-((dt - 0.5) ** 2) / 0.8)

    glucose = base + meal_bump + random.gauss(0, sd)
    return round(max(3.5, min(16.0, glucose)), 2)


# ─────────────────────────────────────────────────────────────────
# Seed 单个用户
# ─────────────────────────────────────────────────────────────────

def seed_user(u: dict, cur) -> None:
    uid = u["user_id"]
    print(f"\n── {uid} ({u['name']}) ──────────────────────")

    # ── users ──────────────────────────────────────────────────
    cur.execute(
        """
        INSERT INTO users
            (user_id, name, birth_year, gender, waist_cm, weight_kg, height_cm,
             avatar, language, onboarding_completed, conditions, medications, preferences)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,TRUE,%s,%s,%s)
        ON CONFLICT (user_id) DO UPDATE SET
            name=EXCLUDED.name, weight_kg=EXCLUDED.weight_kg,
            waist_cm=EXCLUDED.waist_cm, updated_at=NOW()
        """,
        (
            uid, u["name"], u["birth_year"], u["gender"],
            u["waist_cm"], u["weight_kg"], u["height_cm"],
            u["avatar"], u["language"],
            u["conditions"], u["medications"],
            json.dumps(u["preferences"]),
        ),
    )
    print("  ✓ users")

    # ── reward_log ────────────────────────────────────────────
    cur.execute(
        "INSERT INTO reward_log (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
        (uid,),
    )
    print("  ✓ reward_log")

    # ── weekly_patterns ───────────────────────────────────────
    cur.execute("DELETE FROM user_weekly_patterns WHERE user_id=%s", (uid,))
    for p in u["patterns"]:
        cur.execute(
            "INSERT INTO user_weekly_patterns (user_id,day_of_week,start_time,end_time,activity_type) "
            "VALUES (%s,%s,%s,%s,%s)",
            (uid, p["day_of_week"], p["start"], p["end"], p["type"]),
        )
    print(f"  ✓ weekly_patterns ({len(u['patterns'])} 条)")

    # ── known_places ──────────────────────────────────────────
    cur.execute("DELETE FROM user_known_places WHERE user_id=%s", (uid,))
    for name, ptype, lat, lng in u["places"]:
        cur.execute(
            "INSERT INTO user_known_places (user_id,place_name,place_type,gps_lat,gps_lng) "
            "VALUES (%s,%s,%s,%s,%s)",
            (uid, name, ptype, lat, lng),
        )
    print(f"  ✓ known_places ({len(u['places'])} 条)")

    # ── emergency_contacts ────────────────────────────────────
    cur.execute("DELETE FROM user_emergency_contacts WHERE user_id=%s", (uid,))
    for cname, phone, rel, notify in u["contacts"]:
        cur.execute(
            "INSERT INTO user_emergency_contacts (user_id,contact_name,phone_number,relationship,notify_on) "
            "VALUES (%s,%s,%s,%s,%s)",
            (uid, cname, phone, rel, json.dumps(notify)),
        )
    print(f"  ✓ emergency_contacts ({len(u['contacts'])} 条)")

    # ── CGM 过去 7 天（今天不写，保留 data_gap 测试场景）────────
    today_start = datetime.combine(date.today(), time(0, 0))
    cur.execute("DELETE FROM user_cgm_log WHERE user_id=%s", (uid,))
    cgm_rows = []
    profile = u["glucose_profile"]
    for day_offset in range(7, 0, -1):
        day_base = today_start - timedelta(days=day_offset)
        for minute in range(0, 1440, 10):
            ts = day_base + timedelta(minutes=minute)
            cgm_rows.append((uid, ts, _glucose_at(ts, profile), "cgm"))
    cur.executemany(
        "INSERT INTO user_cgm_log (user_id,recorded_at,glucose,source) VALUES (%s,%s,%s,%s)",
        cgm_rows,
    )
    print(f"  ✓ user_cgm_log ({len(cgm_rows)} 条，7 天)")

    # ── HR 过去 7 天 ──────────────────────────────────────────
    cur.execute("DELETE FROM user_hr_log WHERE user_id=%s", (uid,))
    base_lat, base_lng = u["places"][0][2], u["places"][0][3]
    hr_rows = []
    for day_offset in range(7, 0, -1):
        day_base = today_start - timedelta(days=day_offset)
        for minute in range(0, 1440, 10):
            ts = day_base + timedelta(minutes=minute)
            hr = random.randint(62, 78)
            hr_rows.append((
                uid, ts, hr,
                round(base_lat + random.gauss(0, 0.001), 7),
                round(base_lng + random.gauss(0, 0.001), 7),
            ))
    cur.executemany(
        "INSERT INTO user_hr_log (user_id,recorded_at,heart_rate,gps_lat,gps_lng) VALUES (%s,%s,%s,%s,%s)",
        hr_rows,
    )
    print(f"  ✓ user_hr_log ({len(hr_rows)} 条，7 天)")

    # ── 运动记录（从 weekly_patterns 推算 3 次历史）─────────────
    cur.execute("DELETE FROM user_exercise_log WHERE user_id=%s", (uid,))
    exercise_count = 0
    for day_offset in range(7, 0, -1):
        day = date.today() - timedelta(days=day_offset)
        dow = day.weekday()
        for p in u["patterns"]:
            if p["day_of_week"] == dow:
                started = datetime.combine(day, p["start"])
                ended   = datetime.combine(day, p["end"])
                cur.execute(
                    "INSERT INTO user_exercise_log "
                    "(user_id,exercise_type,started_at,ended_at,avg_heart_rate,calories_burned) "
                    "VALUES (%s,%s,%s,%s,%s,%s)",
                    (uid, p["type"], started, ended,
                     random.randint(125, 155), round(random.uniform(280, 480), 1)),
                )
                exercise_count += 1
    print(f"  ✓ user_exercise_log ({exercise_count} 次)")

    # ── 每日血糖统计（回填 7 天）─────────────────────────────────
    cur.execute("DELETE FROM user_glucose_daily_stats WHERE user_id=%s", (uid,))
    for day_offset in range(7, 0, -1):
        stat_date = date.today() - timedelta(days=day_offset)
        day_start = datetime.combine(stat_date, time(0, 0))
        values = [_glucose_at(day_start + timedelta(minutes=m), profile) for m in range(0, 1440, 10)]
        avg_g = round(sum(values) / len(values), 2)
        sd_g  = round(math.sqrt(sum((v - avg_g)**2 for v in values) / len(values)), 2)
        tir   = round(sum(1 for v in values if 3.9 <= v <= 10.0) / len(values) * 100, 1)
        tbr   = round(sum(1 for v in values if v < 3.9) / len(values) * 100, 1)
        tar   = round(100.0 - tir - tbr, 1)
        cur.execute(
            """
            INSERT INTO user_glucose_daily_stats
                (user_id,stat_date,avg_glucose,peak_glucose,nadir_glucose,
                 glucose_sd,tir_percent,tbr_percent,tar_percent,data_points)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (user_id,stat_date) DO UPDATE SET
                avg_glucose=EXCLUDED.avg_glucose, updated_at=NOW()
            """,
            (uid, stat_date, avg_g, max(values), min(values), sd_g, tir, tbr, tar, len(values)),
        )
    print(f"  ✓ user_glucose_daily_stats (7 天)")

    # ── 情绪摘要（供陪伴 Agent 测试）─────────────────────────────
    for summary_date, text, emotion in u["emotion_summaries"]:
        cur.execute(
            """
            INSERT INTO user_emotion_summary (user_id,summary_date,summary_text,primary_emotion)
            VALUES (%s,%s,%s,%s)
            ON CONFLICT (user_id,summary_date) DO UPDATE SET
                summary_text=EXCLUDED.summary_text, primary_emotion=EXCLUDED.primary_emotion
            """,
            (uid, summary_date, text, emotion),
        )
    print(f"  ✓ user_emotion_summary ({len(u['emotion_summaries'])} 条)")


# ─────────────────────────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────────────────────────

def main() -> None:
    print("=== GlucoGardener Seed ===")
    print(f"目标：{os.environ.get('PG_HOST')}:{os.environ.get('PG_PORT')}/{os.environ.get('PG_DB')}\n")

    with db_cursor(commit=True) as cur:
        for user in USERS:
            seed_user(user, cur)

    print("\n✅ 全部 Seed 完成")
    print("   今天的 CGM/HR 数据未写入（保留 data_gap 测试场景）")
    print("   DEMO_MODE=false 后重启 chatbot 即可使用真实数据")


if __name__ == "__main__":
    main()
