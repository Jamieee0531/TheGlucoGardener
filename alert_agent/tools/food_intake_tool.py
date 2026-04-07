"""
alert_agent/tools/food_intake_tool.py

Food Intake Tool.
Queries today's meal records for the user from user_food_log.
Returns structured summary for Reflector's clinical reasoning.
"""

from datetime import datetime, time, timedelta

import structlog
from sqlalchemy import select, func

from alert_db.models import UserFoodLog
from alert_db.session import AsyncSessionLocal
from config import settings

logger = structlog.get_logger(__name__)

# Demo fallback: if demo_mode is on and no food records exist for today,
# return these hardcoded meals so Reflector always has food context.
_DEMO_FALLBACK_MEALS = [
    {"time": "06:30", "food_name": "Kaya Toast + Kopi", "meal_type": "breakfast", "gi_level": "medium", "kcal": 320},
    {"time": "11:30", "food_name": "Chicken Sandwich", "meal_type": "lunch", "gi_level": "medium", "kcal": 350},
]


async def get_food_intake(user_id: str, reference_time: datetime | str = "") -> dict:
    """
    Return today's food intake summary for the given user.
    Returns dict with meals_today, total_kcal, last_meal_hours_ago.
    """
    if isinstance(reference_time, str):
        ref_time = datetime.fromisoformat(reference_time) if reference_time else datetime.now()
    else:
        ref_time = reference_time

    today_start = datetime.combine(ref_time.date(), time(0, 0))
    today_end = datetime.combine(ref_time.date() + timedelta(days=1), time(0, 0))

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(UserFoodLog)
            .where(
                UserFoodLog.user_id == user_id,
                UserFoodLog.recorded_at >= today_start,
                UserFoodLog.recorded_at < today_end,
            )
            .order_by(UserFoodLog.recorded_at.asc())
        )
        rows = result.scalars().all()

    if not rows:
        if settings.demo_mode:
            logger.info("food_intake_demo_fallback", user_id=user_id)
            total = sum(m["kcal"] for m in _DEMO_FALLBACK_MEALS)
            # Assume last meal at 11:30 on ref_time's date
            last_meal_at = datetime.combine(ref_time.date(), time(11, 30))
            hours_ago = round((ref_time - last_meal_at).total_seconds() / 3600, 1)
            return {
                "meals_today": _DEMO_FALLBACK_MEALS,
                "total_kcal": total,
                "last_meal_hours_ago": max(hours_ago, 0),
            }
        return {
            "meals_today": [],
            "total_kcal": 0,
            "last_meal_hours_ago": None,
        }

    meals = []
    for r in rows:
        meals.append({
            "time": r.recorded_at.strftime("%H:%M"),
            "food_name": r.food_name,
            "meal_type": r.meal_type,
            "gi_level": r.gi_level,
            "kcal": float(r.total_calories),
        })

    total_kcal = sum(m["kcal"] for m in meals)
    last_meal_at = rows[-1].recorded_at
    last_meal_hours_ago = round((ref_time - last_meal_at).total_seconds() / 3600, 1)

    return {
        "meals_today": meals,
        "total_kcal": round(total_kcal, 1),
        "last_meal_hours_ago": last_meal_hours_ago,
    }
