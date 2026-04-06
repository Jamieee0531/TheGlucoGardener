"""
chatbot/db/seed_user_001.py

Demo 用户 user_001 — 陈女士（Mdm Chen）
符合演示脚本三个 Moment 的测试数据：
  Moment 1a  情绪支持：女儿未来电，独居，情绪低落
  Moment 1b  食物识别：晚餐云吞面拍照
  Moment 1c  症状推理：饭后站立头晕（体位性低血压，非低血糖）

Usage:
  cd TheGlucoGardener
  python -m chatbot.db.seed_user_001
"""
from __future__ import annotations

import json
import math
import os
import random
import sys
from datetime import date, datetime, time, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
load_dotenv()

from chatbot.db.connection import db_cursor

random.seed(7)

# ── 基本信息 ──────────────────────────────────────────────────────
UID        = "user_001"
TODAY      = date.today()
NOW        = datetime.now().replace(second=0, microsecond=0)
TODAY_7PM  = datetime.combine(TODAY, time(19, 0))   # 演示场景时间点

# 血糖参数：控制一般（5年病史，偶有餐后偏高）
GLUCOSE_PROFILE = {"baseline": 6.8, "meal_spike": 3.0, "sd": 0.45}


# ─────────────────────────────────────────────────────────────────
# 血糖模拟（同 seed.py 逻辑）
# ─────────────────────────────────────────────────────────────────

def _glucose_at(ts: datetime) -> float:
    h    = ts.hour + ts.minute / 60.0
    base = GLUCOSE_PROFILE["baseline"]
    spike = GLUCOSE_PROFILE["meal_spike"]
    sd   = GLUCOSE_PROFILE["sd"]

    meal_bump = 0.0
    for meal_h in (7.5, 13.0, 19.0):
        dt = h - meal_h
        if -0.5 <= dt <= 2.5:
            meal_bump += spike * math.exp(-((dt - 0.5) ** 2) / 0.8)

    glucose = base + meal_bump + random.gauss(0, sd)
    return round(max(3.5, min(16.0, glucose)), 2)


# ─────────────────────────────────────────────────────────────────
# 清理旧数据
# ─────────────────────────────────────────────────────────────────

def purge_old_users(cur) -> None:
    old_ids = ["demo_en", "demo_zh", "demo_ms", "demo_ta"]
    for uid in old_ids:
        cur.execute("DELETE FROM users WHERE user_id = %s", (uid,))
    print(f"  ✓ 已删除旧用户：{old_ids}")


# ─────────────────────────────────────────────────────────────────
# Seed user_001
# ─────────────────────────────────────────────────────────────────

def seed(cur) -> None:

    # ── users ────────────────────────────────────────────────────
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
            UID, "Mdm Chen", 1958, "female",
            88.0, 62.0, 158.0,
            "avatar_1", "English",
            ["Type 2 Diabetes"],
            ["Metformin 500mg"],
            json.dumps({"diet": "low_gi", "lives_alone": True}),
        ),
    )
    print("  ✓ users")

    # ── reward_log ───────────────────────────────────────────────
    cur.execute(
        "INSERT INTO reward_log (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
        (UID,),
    )
    print("  ✓ reward_log")

    # ── weekly_patterns（轻量散步，周一/三/五早上）───────────────
    cur.execute("DELETE FROM user_weekly_patterns WHERE user_id=%s", (UID,))
    patterns = [
        (0, time(7, 30), time(8, 0),  "cardio"),
        (2, time(7, 30), time(8, 0),  "cardio"),
        (4, time(7, 30), time(8, 0),  "cardio"),
    ]
    for dow, start, end, atype in patterns:
        cur.execute(
            "INSERT INTO user_weekly_patterns (user_id,day_of_week,start_time,end_time,activity_type) "
            "VALUES (%s,%s,%s,%s,%s)",
            (UID, dow, start, end, atype),
        )
    print(f"  ✓ weekly_patterns ({len(patterns)} 条)")

    # ── known_places ─────────────────────────────────────────────
    cur.execute("DELETE FROM user_known_places WHERE user_id=%s", (UID,))
    places = [
        ("Home",    "home",   1.3200, 103.8400),
        ("Clinic",  "office", 1.3100, 103.8300),
    ]
    for name, ptype, lat, lng in places:
        cur.execute(
            "INSERT INTO user_known_places (user_id,place_name,place_type,gps_lat,gps_lng) "
            "VALUES (%s,%s,%s,%s,%s)",
            (UID, name, ptype, lat, lng),
        )
    print(f"  ✓ known_places ({len(places)} 条)")

    # ── emergency_contacts（女儿在澳洲）─────────────────────────
    cur.execute("DELETE FROM user_emergency_contacts WHERE user_id=%s", (UID,))
    contacts = [
        ("Chen Mei Ling", "+61412345678", "family",
         ["hard_low_glucose", "hard_high_hr", "data_gap"]),
    ]
    for cname, phone, rel, notify in contacts:
        cur.execute(
            "INSERT INTO user_emergency_contacts "
            "(user_id,contact_name,phone_number,relationship,notify_on) "
            "VALUES (%s,%s,%s,%s,%s)",
            (UID, cname, phone, rel, json.dumps(notify)),
        )
    print(f"  ✓ emergency_contacts ({len(contacts)} 条)")

    # ── CGM：过去 7 天（每 10 分钟）+ 今天到 19:30（饭后高峰）──
    cur.execute("DELETE FROM user_cgm_log WHERE user_id=%s", (UID,))
    cgm_rows = []

    # 过去 7 天
    for day_offset in range(7, 0, -1):
        day_base = datetime.combine(TODAY - timedelta(days=day_offset), time(0, 0))
        for minute in range(0, 1440, 10):
            ts = day_base + timedelta(minutes=minute)
            cgm_rows.append((UID, ts, _glucose_at(ts), "cgm"))

    # 今天 0:00 → 19:30（演示场景：饭后血糖偏高约 9.5，非低血糖）
    day_base = datetime.combine(TODAY, time(0, 0))
    for minute in range(0, 19 * 60 + 30 + 1, 10):
        ts = day_base + timedelta(minutes=minute)
        cgm_rows.append((UID, ts, _glucose_at(ts), "cgm"))

    cur.executemany(
        "INSERT INTO user_cgm_log (user_id,recorded_at,glucose,source) VALUES (%s,%s,%s,%s)",
        cgm_rows,
    )
    print(f"  ✓ user_cgm_log ({len(cgm_rows)} 条，7天+今天至19:30)")

    # ── HR：过去 7 天 ─────────────────────────────────────────────
    cur.execute("DELETE FROM user_hr_log WHERE user_id=%s", (UID,))
    base_lat, base_lng = 1.3200, 103.8400
    hr_rows = []
    for day_offset in range(7, 0, -1):
        day_base = datetime.combine(TODAY - timedelta(days=day_offset), time(0, 0))
        for minute in range(0, 1440, 10):
            ts = day_base + timedelta(minutes=minute)
            hr = random.randint(60, 75)
            hr_rows.append((
                UID, ts, hr,
                round(base_lat + random.gauss(0, 0.001), 7),
                round(base_lng + random.gauss(0, 0.001), 7),
            ))
    cur.executemany(
        "INSERT INTO user_hr_log (user_id,recorded_at,heart_rate,gps_lat,gps_lng) "
        "VALUES (%s,%s,%s,%s,%s)",
        hr_rows,
    )
    print(f"  ✓ user_hr_log ({len(hr_rows)} 条，7 天)")

    # ── exercise_log（按 weekly_patterns 回填 7 天）──────────────
    cur.execute("DELETE FROM user_exercise_log WHERE user_id=%s", (UID,))
    ex_count = 0
    for day_offset in range(7, 0, -1):
        day = TODAY - timedelta(days=day_offset)
        dow = day.weekday()
        for p_dow, p_start, p_end, p_type in patterns:
            if p_dow == dow:
                cur.execute(
                    "INSERT INTO user_exercise_log "
                    "(user_id,exercise_type,started_at,ended_at,avg_heart_rate,calories_burned) "
                    "VALUES (%s,%s,%s,%s,%s,%s)",
                    (UID, p_type,
                     datetime.combine(day, p_start),
                     datetime.combine(day, p_end),
                     random.randint(95, 115),
                     round(random.uniform(100, 180), 1)),
                )
                ex_count += 1
    print(f"  ✓ user_exercise_log ({ex_count} 次)")

    # ── 每日血糖统计（过去 7 天）─────────────────────────────────
    cur.execute("DELETE FROM user_glucose_daily_stats WHERE user_id=%s", (UID,))
    for day_offset in range(7, 0, -1):
        stat_date = TODAY - timedelta(days=day_offset)
        day_start = datetime.combine(stat_date, time(0, 0))
        values = [_glucose_at(day_start + timedelta(minutes=m)) for m in range(0, 1440, 10)]
        avg_g = round(sum(values) / len(values), 2)
        sd_g  = round(math.sqrt(sum((v - avg_g) ** 2 for v in values) / len(values)), 2)
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
            (UID, stat_date, avg_g, max(values), min(values), sd_g, tir, tbr, tar, len(values)),
        )
    print("  ✓ user_glucose_daily_stats (7 天)")

    # ── emotion_summary（近 3 天：孤独感，演示当天情绪铺垫）──────
    cur.execute("DELETE FROM user_emotion_summary WHERE user_id=%s", (UID,))
    summaries = [
        (TODAY - timedelta(days=2),
         "Felt lonely in the evening. Daughter did not call as expected.",
         "sad"),
        (TODAY - timedelta(days=1),
         "Mood improved after morning walk and chat with neighbour.",
         "neutral"),
        (TODAY,
         "Waiting for daughter's call all day. Feeling forgotten and isolated by evening.",
         "sad"),
    ]
    for s_date, s_text, s_emotion in summaries:
        cur.execute(
            """
            INSERT INTO user_emotion_summary (user_id,summary_date,summary_text,primary_emotion)
            VALUES (%s,%s,%s,%s)
            ON CONFLICT (user_id,summary_date) DO UPDATE SET
                summary_text=EXCLUDED.summary_text, primary_emotion=EXCLUDED.primary_emotion
            """,
            (UID, s_date, s_text, s_emotion),
        )
    print(f"  ✓ user_emotion_summary ({len(summaries)} 条)")

    # ── food_log（今晚 7pm 云吞面，演示 Moment 1b）───────────────
    cur.execute("DELETE FROM user_food_log WHERE user_id=%s", (UID,))
    cur.execute(
        """
        INSERT INTO user_food_log (user_id,recorded_at,food_name,meal_type,gi_level,total_calories)
        VALUES (%s,%s,%s,%s,%s,%s)
        """,
        (UID, TODAY_7PM, "Wonton Noodles (云吞面)", "dinner", "high", 480.0),
    )
    print("  ✓ user_food_log (云吞面 19:00)")


# ─────────────────────────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────────────────────────

def main() -> None:
    print("=== GlucoGardener Seed — user_001 (Mdm Chen) ===")
    print(f"目标：{os.environ.get('PG_HOST')}:{os.environ.get('PG_PORT')}/{os.environ.get('PG_DB')}\n")

    with db_cursor(commit=True) as cur:
        print("── 清理旧 Demo 用户 ──")
        purge_old_users(cur)
        print(f"\n── user_001 ({TODAY}) ──")
        seed(cur)

    print("\n✅ Seed 完成")
    print(f"   user_001 = Mdm Chen | 血糖今日数据截至 19:30 | 云吞面晚餐已写入")


if __name__ == "__main__":
    main()
