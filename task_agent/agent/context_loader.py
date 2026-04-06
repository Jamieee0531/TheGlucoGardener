from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from datetime import date, datetime, timedelta
from task_agent.db.models import User


async def fetch_context(db: AsyncSession, user_id: str) -> Dict[str, Any]:
    # 1. User profile
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()

    bmi = user.bmi if user else 22.0
    profile = {
        "name": user.name if user else "User",
        "gender": user.gender if user else "other",
        "weight_kg": float(user.weight_kg) if user and user.weight_kg else 70.0,
        "height_cm": float(user.height_cm) if user and user.height_cm else 170.0,
        "bmi": bmi,
        "waist_cm": float(user.waist_cm) if user and user.waist_cm else None,
        "birth_year": user.birth_year if user else None,
        "language_pref": user.language_pref if user else "en",
    }

    today_start = datetime.combine(date.today(), datetime.min.time())
    two_hours_ago = datetime.utcnow() - timedelta(hours=2)

    # 2. Calories burned today
    cbt = await db.scalar(text("""
        SELECT COALESCE(SUM(calories_burned), 0)
        FROM user_exercise_log
        WHERE user_id = :u AND started_at >= :today
    """).bindparams(u=user_id, today=today_start))

    # 3. BG avg last 2h
    bg = await db.scalar(text("""
        SELECT AVG(glucose)
        FROM user_cgm_log
        WHERE user_id = :u AND recorded_at >= :cutoff
    """).bindparams(u=user_id, cutoff=two_hours_ago))

    # 4. Last 3 walking sessions (duration computed in Python for DB portability)
    rows = await db.execute(text("""
        SELECT exercise_type, calories_burned, started_at, ended_at
        FROM user_exercise_log
        WHERE user_id = :u AND exercise_type = 'walking'
        ORDER BY started_at DESC
        LIMIT 3
    """).bindparams(u=user_id))
    history = []
    for h in rows.fetchall():
        try:
            duration_min = round((h.ended_at - h.started_at).total_seconds() / 60)
        except Exception:
            duration_min = 10
        history.append({
            "type": h.exercise_type,
            "duration_min": duration_min,
            "calories_burned": float(h.calories_burned or 0),
        })

    # 5. Latest GPS from HR log
    gps_row = (await db.execute(text("""
        SELECT gps_lat, gps_lng
        FROM user_hr_log
        WHERE user_id = :u AND gps_lat IS NOT NULL
        ORDER BY recorded_at DESC LIMIT 1
    """).bindparams(u=user_id))).fetchone()

    last_gps = (
        {"lat": float(gps_row.gps_lat), "lng": float(gps_row.gps_lng)}
        if gps_row
        else {"lat": 1.3521, "lng": 103.8198}
    )

    return {
        "user_profile": profile,
        "calories_burned_today": float(cbt or 0.0),
        "avg_bg_last_2h": float(bg) if bg else None,
        "exercise_history": history,
        "last_gps": last_gps,
    }
