"""
demo/seed_user_002.py

测试账户 002 (Marcus) 的数据注入脚本。直接写入 PostgreSQL，绕过 Gateway API。
生成 21 天历史 CGM、心率、运动记录，以及用户档案、每周运动计划、已知地点、
紧急联系人、饮食记录、情绪记录、Pipeline 聚合表、积分、好友关系。

Marcus 的故事:
- 58 岁仓库主管, T2D 确诊 3 年, 每周健身 3-4 次
- Mon/Wed/Sat 做 HIIT (14:00-14:45)，Thu 做 cardio (18:00-19:00)
- 过去 3 次 HIIT 期间血糖平均下降 1.03 mmol/L
- 这个数据支撑 soft_trigger_pre_exercise 场景的 Agent 推理

【环境变量依赖】
运行前请确保项目根目录下的 .env 文件配置了以下 PostgreSQL 连接参数：
    PG_HOST     数据库地址（本地填 127.0.0.1，云端填 RDS 公网 IP）
    PG_PORT     数据库端口（默认 5432）
    PG_USER     数据库用户名
    PG_PASSWORD 数据库密码
    PG_DB       数据库名称

Usage: python demo/seed_user_002.py
"""

import asyncio
import random
import sys
from datetime import date, datetime, time, timedelta

sys.path.insert(0, ".")

from sqlalchemy import delete

from alert_db.models import (
    RewardLog,
    User,
    UserCGMLog,
    UserEmergencyContact,
    UserEmotionLog,
    UserExerciseLog,
    UserFoodLog,
    UserFriend,
    UserGlucoseDailyStats,
    UserGlucoseWeeklyProfile,
    UserHRLog,
    UserKnownPlace,
    UserWeeklyPattern,
)
from alert_db.session import AsyncSessionLocal

# ── Constants ───────────────────────────────────────────────
USER_ID = "user_002"
HISTORY_DAYS = 21

# GPS coordinates
HOME_LAT, HOME_LNG = 1.3521, 103.8198
GYM_LAT, GYM_LNG = 1.3200, 103.8400
WAREHOUSE_LAT, WAREHOUSE_LNG = 1.2800, 103.8500

# HIIT glucose drop targets (avg = 1.03)
# Applied to ALL hiit sessions (not just Saturdays)
# because _get_exercise_history picks the last 3 matching sessions by type
HIIT_DROPS = [
    {"pre": 6.20, "post": 5.15},  # drop 1.05
    {"pre": 5.80, "post": 4.85},  # drop 0.95
    {"pre": 6.00, "post": 4.90},  # drop 1.10
]

# Food menu rotation
MEALS = {
    "breakfast": [
        ("Kaya Toast + Kopi", "medium", 320),
        ("Oatmeal with Banana", "low", 280),
        ("Roti Prata + Teh", "high", 380),
        ("Wholemeal Bread + Eggs", "low", 310),
    ],
    "lunch": [
        ("Chicken Rice", "medium", 650),
        ("Nasi Lemak", "high", 700),
        ("Fish Soup Bee Hoon", "low", 480),
        ("Economy Rice (2 veg 1 meat)", "medium", 580),
    ],
    "dinner": [
        ("Fish Soup Bee Hoon", "low", 480),
        ("Steamed Fish + Brown Rice", "low", 450),
        ("Bak Kut Teh + Rice", "medium", 550),
        ("Yong Tau Foo (soup)", "low", 420),
    ],
    "snack": [
        ("Banana", "medium", 105),
        ("Mixed Nuts", "low", 160),
    ],
}


def _clamp(v: float, lo: float = 3.5, hi: float = 12.0) -> float:
    return max(lo, min(hi, v))


def _baseline_glucose(hour: int) -> float:
    """Return mean glucose for a given hour of day (non-exercise baseline)."""
    if hour < 7:
        return 5.8 + random.gauss(0, 0.3)
    elif hour < 9:
        return 7.2 + random.gauss(0, 0.4)
    elif hour < 12:
        return 6.0 + random.gauss(0, 0.3)
    elif hour < 14:
        return 7.5 + random.gauss(0, 0.4)
    elif hour < 18:
        return 6.2 + random.gauss(0, 0.3)
    elif hour < 20:
        return 7.8 + random.gauss(0, 0.5)
    else:
        return 6.0 + random.gauss(0, 0.3)


def _find_past_hiit_days(today: date, count: int) -> list[date]:
    """Return the most recent `count` hiit days before today, newest first."""
    hiit_days = []
    d = today - timedelta(days=1)
    while len(hiit_days) < count:
        # Mon(0), Wed(2), Sat(5) are hiit days
        if d.weekday() in (0, 2, 5):
            hiit_days.append(d)
        d -= timedelta(days=1)
    return hiit_days


def _exercise_schedule(d: date) -> list[tuple[str, time, time]]:
    """Return list of (activity_type, start_time, end_time) for a given date's dow."""
    dow = d.weekday()
    schedule = {
        0: [("hiit", time(14, 0), time(14, 45))],    # Mon
        2: [("hiit", time(14, 0), time(14, 45))],    # Wed
        3: [("cardio", time(18, 0), time(19, 0))],   # Thu
        5: [("hiit", time(14, 0), time(14, 45))],    # Sat
    }
    return schedule.get(dow, [])


async def seed() -> None:
    """注入 user_002 (Marcus) 的测试数据。"""
    async with AsyncSessionLocal() as session:
        print(f"Seeding data for {USER_ID} (Marcus)...")

        # ── 0. Clean up old data ──────────────────────────────
        cleanup_tables = [
            RewardLog, UserFriend, UserEmotionLog, UserFoodLog,
            UserExerciseLog, UserHRLog, UserCGMLog,
            UserGlucoseWeeklyProfile, UserGlucoseDailyStats,
            UserKnownPlace, UserEmergencyContact, UserWeeklyPattern,
        ]
        for model in cleanup_tables:
            await session.execute(
                delete(model).where(model.user_id == USER_ID)
            )
        await session.commit()
        print("  ✓ Cleaned up old data for user_002")

        today = datetime.now().date()
        today_start = datetime.combine(today, time(0, 0))
        past_hiit_days = _find_past_hiit_days(today, 3)

        # ── 1. User Profile ────────────────────────────────────
        user = User(
            user_id=USER_ID,
            name="Marcus",
            birth_year=1968,
            gender="male",
            waist_cm=92.0,
            weight_kg=85.0,
            height_cm=178.0,
            avatar="avatar_2",
            language="English",
            onboarding_completed=True,
        )
        await session.merge(user)
        await session.commit()
        print("  ✓ User profile (Marcus, 58y, 85kg/178cm)")

        # ── 2. Weekly Patterns ─────────────────────────────────
        patterns = [
            (0, time(14, 0), time(14, 45), "hiit"),    # Mon
            (2, time(14, 0), time(14, 45), "hiit"),    # Wed
            (3, time(18, 0), time(19, 0), "cardio"),   # Thu
            (5, time(14, 0), time(14, 45), "hiit"),    # Sat
        ]
        for dow, st, et, atype in patterns:
            session.add(UserWeeklyPattern(
                user_id=USER_ID,
                day_of_week=dow,
                start_time=st,
                end_time=et,
                activity_type=atype,
            ))
        await session.commit()
        print("  ✓ Weekly patterns (Mon/Wed/Sat 14:00 HIIT, Thu 18:00 cardio)")

        # ── 3. Known Places ────────────────────────────────────
        places = [
            ("Home", "home", HOME_LAT, HOME_LNG),
            ("ActiveSG Gym", "gym", GYM_LAT, GYM_LNG),
            ("Warehouse", "office", WAREHOUSE_LAT, WAREHOUSE_LNG),
        ]
        for name, ptype, lat, lng in places:
            session.add(UserKnownPlace(
                user_id=USER_ID,
                place_name=name,
                place_type=ptype,
                gps_lat=lat,
                gps_lng=lng,
            ))
        await session.commit()
        print("  ✓ Known places (Home, ActiveSG Gym, Warehouse)")

        # ── 4. Emergency Contact ───────────────────────────────
        session.add(UserEmergencyContact(
            user_id=USER_ID,
            contact_name="Linda",
            phone_number="+6591234567",
            relationship="family",
            notify_on=["hard_low_glucose", "hard_high_hr", "data_gap"],
        ))
        await session.commit()
        print("  ✓ Emergency contact (Linda)")

        # ── 5. Historical CGM (past 21 days, NOT today) ───────
        cgm_records = []
        all_day_glucose: dict[date, list[float]] = {}

        for day_offset in range(HISTORY_DAYS, 0, -1):
            d = today - timedelta(days=day_offset)
            day_base = datetime.combine(d, time(0, 0))
            day_glucose = []

            # Check if this is one of the 3 target hiit days
            hiit_idx = None
            if d in past_hiit_days:
                hiit_idx = past_hiit_days.index(d)

            for minute_offset in range(0, 1440, 10):
                ts = day_base + timedelta(minutes=minute_offset)
                hour = ts.hour
                minute = ts.minute

                # HIIT exercise window: craft specific drop curve
                if hiit_idx is not None and 13 <= hour <= 16:
                    drop_cfg = HIIT_DROPS[hiit_idx]
                    pre_val = drop_cfg["pre"]
                    post_val = drop_cfg["post"]

                    if hour == 13 and minute < 50:
                        # 13:00-13:50: settle from lunch to pre-exercise value
                        frac = minute / 50.0
                        glucose = 7.5 - (7.5 - pre_val) * frac + random.gauss(0, 0.08)
                    elif hour == 13 and minute >= 50 or hour == 14 and minute == 0:
                        # 13:50-14:00: at pre-exercise level
                        glucose = pre_val + random.gauss(0, 0.05)
                    elif hour == 14 and minute <= 45:
                        # 14:00-14:45: steep drop during HIIT
                        mins_into_ex = minute
                        total_ex_mins = 45
                        frac = min(mins_into_ex / total_ex_mins, 1.0)
                        glucose = pre_val - (pre_val - post_val) * frac + random.gauss(0, 0.06)
                    elif (hour == 14 and minute > 45) or hour == 15 or hour == 16:
                        # 14:45-16:59: recovery, slow rise
                        mins_after = (hour - 14) * 60 + minute - 45
                        recovery = min(mins_after / 75.0, 1.0) * 0.5
                        glucose = post_val + recovery + random.gauss(0, 0.1)
                    else:
                        glucose = _baseline_glucose(hour)
                # Other exercise days (cardio on Thu): mild drop during exercise
                elif _exercise_schedule(d) and any(
                    st <= ts.time() <= et for _, st, et in _exercise_schedule(d)
                ) and hiit_idx is None:
                    glucose = 5.8 + random.gauss(0, 0.3)  # general exercise dip
                else:
                    glucose = _baseline_glucose(hour)

                glucose = round(_clamp(glucose), 2)
                day_glucose.append(glucose)
                cgm_records.append(UserCGMLog(
                    user_id=USER_ID,
                    recorded_at=ts,
                    glucose=glucose,
                ))

            all_day_glucose[d] = day_glucose

        session.add_all(cgm_records)
        await session.commit()
        print(f"  ✓ CGM records: {len(cgm_records)} entries (21 days)")

        # ── 6. Historical HR (past 21 days, NOT today) ─────────
        hr_records = []
        for day_offset in range(HISTORY_DAYS, 0, -1):
            d = today - timedelta(days=day_offset)
            day_base = datetime.combine(d, time(0, 0))
            exercises = _exercise_schedule(d)

            for minute_offset in range(0, 1440, 10):
                ts = day_base + timedelta(minutes=minute_offset)
                t = ts.time()

                # During exercise: elevated HR + gym GPS
                in_exercise = any(st <= t <= et for _, st, et in exercises)
                if in_exercise:
                    hr = random.randint(125, 160)
                    lat = GYM_LAT + random.gauss(0, 0.0005)
                    lng = GYM_LNG + random.gauss(0, 0.0005)
                # Daytime at warehouse/home
                elif 8 <= ts.hour <= 17:
                    hr = random.randint(65, 82)
                    lat = WAREHOUSE_LAT + random.gauss(0, 0.001)
                    lng = WAREHOUSE_LNG + random.gauss(0, 0.001)
                else:
                    hr = random.randint(58, 75)
                    lat = HOME_LAT + random.gauss(0, 0.001)
                    lng = HOME_LNG + random.gauss(0, 0.001)

                hr_records.append(UserHRLog(
                    user_id=USER_ID,
                    recorded_at=ts,
                    heart_rate=hr,
                    gps_lat=round(lat, 7),
                    gps_lng=round(lng, 7),
                ))

        session.add_all(hr_records)
        await session.commit()
        print(f"  ✓ HR records: {len(hr_records)} entries (21 days)")

        # ── 7. Exercise Log (past 21 days) ─────────────────────
        ex_count = 0
        for day_offset in range(HISTORY_DAYS, 0, -1):
            d = today - timedelta(days=day_offset)
            for atype, st, et in _exercise_schedule(d):
                start_dt = datetime.combine(d, st)
                end_dt = datetime.combine(d, et)
                if atype == "cardio":
                    avg_hr = random.randint(140, 160)
                    cal = round(random.uniform(300, 380), 1)
                else:
                    avg_hr = random.randint(130, 155)
                    cal = round(random.uniform(380, 450), 1)
                session.add(UserExerciseLog(
                    user_id=USER_ID,
                    exercise_type=atype,
                    started_at=start_dt,
                    ended_at=end_dt,
                    avg_heart_rate=avg_hr,
                    calories_burned=cal,
                ))
                ex_count += 1
        await session.commit()
        print(f"  ✓ Exercise log: {ex_count} sessions (21 days)")

        # ── 8. Food Log (past 7 days) ──────────────────────────
        food_count = 0
        for day_offset in range(7, 0, -1):
            d = today - timedelta(days=day_offset)
            # Breakfast
            fname, gi, cal = random.choice(MEALS["breakfast"])
            session.add(UserFoodLog(
                user_id=USER_ID,
                recorded_at=datetime.combine(d, time(7, 30)),
                food_name=fname, meal_type="breakfast",
                gi_level=gi, total_calories=cal,
            ))
            food_count += 1
            # Lunch
            fname, gi, cal = random.choice(MEALS["lunch"])
            session.add(UserFoodLog(
                user_id=USER_ID,
                recorded_at=datetime.combine(d, time(12, 30)),
                food_name=fname, meal_type="lunch",
                gi_level=gi, total_calories=cal,
            ))
            food_count += 1
            # Dinner
            fname, gi, cal = random.choice(MEALS["dinner"])
            session.add(UserFoodLog(
                user_id=USER_ID,
                recorded_at=datetime.combine(d, time(19, 0)),
                food_name=fname, meal_type="dinner",
                gi_level=gi, total_calories=cal,
            ))
            food_count += 1
            # Snack (~50% chance)
            if random.random() > 0.5:
                fname, gi, cal = random.choice(MEALS["snack"])
                session.add(UserFoodLog(
                    user_id=USER_ID,
                    recorded_at=datetime.combine(d, time(16, 0)),
                    food_name=fname, meal_type="snack",
                    gi_level=gi, total_calories=cal,
                ))
                food_count += 1
        # ── 8b. Today's Food Log (demo scenario) ─────────────────
        # Marcus had an early breakfast and a light lunch before
        # the soft_trigger_pre_exercise scenario fires at ~13:31.
        # This ensures food_intake_tool returns meaningful data for
        # the Reflector to reason about (low total kcal, early meals).
        session.add(UserFoodLog(
            user_id=USER_ID,
            recorded_at=datetime.combine(today, time(6, 30)),
            food_name="Kaya Toast + Kopi",
            meal_type="breakfast",
            gi_level="medium",
            total_calories=320,
        ))
        session.add(UserFoodLog(
            user_id=USER_ID,
            recorded_at=datetime.combine(today, time(11, 30)),
            food_name="Chicken Sandwich",
            meal_type="lunch",
            gi_level="medium",
            total_calories=350,
        ))
        food_count += 2
        await session.commit()
        print(f"  ✓ Food log: {food_count} entries (7 days + today)")

        # ── 9. Emotion Log (past 3 days) ───────────────────────
        emotions = [
            (1, "Feeling a bit tired after the long shift", "neutral"),
            (2, "Good workout today, pushed through", "positive"),
            (3, "Annoyed that I had to skip lunch break", "frustrated"),
        ]
        for day_off, text, label in emotions:
            session.add(UserEmotionLog(
                user_id=USER_ID,
                recorded_at=datetime.combine(
                    today - timedelta(days=day_off), time(20, 0)
                ),
                user_input=text,
                emotion_label=label,
            ))
        await session.commit()
        print("  ✓ Emotion log: 3 entries")

        # ── 10. Pipeline: Daily Stats (past 21 days) ──────────
        for day_offset in range(HISTORY_DAYS, 0, -1):
            d = today - timedelta(days=day_offset)
            readings = all_day_glucose.get(d, [])
            if not readings:
                continue
            avg_g = round(sum(readings) / len(readings), 2)
            peak_g = round(max(readings), 2)
            nadir_g = round(min(readings), 2)
            mean_g = avg_g
            sd_g = round(
                (sum((x - mean_g) ** 2 for x in readings) / len(readings)) ** 0.5, 2
            )
            tir = round(
                sum(1 for x in readings if 3.9 <= x <= 10.0) / len(readings) * 100, 1
            )
            tbr = round(
                sum(1 for x in readings if x < 3.9) / len(readings) * 100, 1
            )
            tar = round(
                sum(1 for x in readings if x > 10.0) / len(readings) * 100, 1
            )
            session.add(UserGlucoseDailyStats(
                user_id=USER_ID,
                stat_date=d,
                avg_glucose=avg_g,
                peak_glucose=peak_g,
                nadir_glucose=nadir_g,
                glucose_sd=sd_g,
                tir_percent=tir,
                tbr_percent=tbr,
                tar_percent=tar,
                data_points=len(readings),
                is_realtime=False,
            ))
        await session.commit()
        print(f"  ✓ Daily glucose stats: {HISTORY_DAYS} days")

        # ── 11. Pipeline: Weekly Profile (2 entries) ───────────
        for week_end_offset in [1, 8]:
            profile_date = today - timedelta(days=week_end_offset)
            window_start = profile_date - timedelta(days=6)

            # Gather 7 days of readings
            week_readings = []
            for d_off in range(7):
                d = window_start + timedelta(days=d_off)
                week_readings.extend(all_day_glucose.get(d, []))

            if not week_readings:
                continue

            avg_g = round(sum(week_readings) / len(week_readings), 2)
            peak_g = round(max(week_readings), 2)
            nadir_g = round(min(week_readings), 2)
            mean_g = avg_g
            sd_g = round(
                (sum((x - mean_g) ** 2 for x in week_readings) / len(week_readings))
                ** 0.5,
                2,
            )
            cv = round(sd_g / mean_g * 100, 1) if mean_g > 0 else 0
            tir = round(
                sum(1 for x in week_readings if 3.9 <= x <= 10.0)
                / len(week_readings)
                * 100,
                1,
            )
            tbr = round(
                sum(1 for x in week_readings if x < 3.9)
                / len(week_readings)
                * 100,
                1,
            )
            tar = round(
                sum(1 for x in week_readings if x > 10.0)
                / len(week_readings)
                * 100,
                1,
            )
            coverage = round(len(week_readings) / 1008 * 100, 1)

            session.add(UserGlucoseWeeklyProfile(
                user_id=USER_ID,
                profile_date=profile_date,
                window_start=window_start,
                avg_glucose=avg_g,
                peak_glucose=peak_g,
                nadir_glucose=nadir_g,
                glucose_sd=sd_g,
                cv_percent=cv,
                tir_percent=tir,
                tbr_percent=tbr,
                tar_percent=tar,
                avg_delta_vs_prior_7d=round(random.uniform(-0.3, 0.1), 2),
                data_points=len(week_readings),
                coverage_percent=coverage,
            ))
        await session.commit()
        print("  ✓ Weekly glucose profiles: 2 entries")

        # ── 12. Reward Log ─────────────────────────────────────
        await session.merge(RewardLog(
            user_id=USER_ID,
            total_points=320,
            accumulated_points=480,
            consumed_points=160,
        ))
        await session.commit()
        print("  ✓ Reward log (320 pts available)")

        # ── 13. Friends ────────────────────────────────────────
        for friend_id in ["user_001", "user_003"]:
            session.add(UserFriend(
                user_id=USER_ID,
                friend_id=friend_id,
            ))
        await session.commit()
        print("  ✓ Friends (user_001, user_003)")

        # ── Summary ────────────────────────────────────────────
        print(f"\n✅ Seed complete for {USER_ID} (Marcus)")
        print("   Note: No data written for today — scenarios inject today's data.")
        print(f"   Past 3 HIIT days used for exercise drop pattern: {past_hiit_days}")
        print(f"\n   Next step: python demo/seed_user_002.py  (done!)")
        print(f"   Then run scenarios via frontend ScenarioPlayer.")


if __name__ == "__main__":
    random.seed(42)  # reproducible data
    asyncio.run(seed())
