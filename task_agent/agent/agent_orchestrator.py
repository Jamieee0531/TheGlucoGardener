import logging
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from task_agent.db.models import DynamicTaskLog, RewardLog
from task_agent.utils.math import haversine

logger = logging.getLogger(__name__)


async def daily_task_guard(db: AsyncSession, user_id: str) -> bool:
    """Returns True (skip) if a dynamic task already exists for this user today."""
    stmt = select(DynamicTaskLog.task_id).where(
        DynamicTaskLog.user_id == user_id,
        func.date(DynamicTaskLog.created_at) == date.today(),
    ).limit(1)
    exists = await db.scalar(stmt)
    return exists is not None


def _log_skip(user_id: str, trigger_source: str, reason: str) -> None:
    logger.info(f"Skipped trigger for {user_id} via {trigger_source}: {reason}")


from task_agent.agent.context_loader import fetch_context
from task_agent.agent.rule_engine import get_rule_for_user, calculate
from task_agent.agent.map_tool import find_nearby_parks
from task_agent.agent.nodes.task_publisher import end_of_today


async def run(db: AsyncSession, user_id: str, trigger_source: str) -> None:
    if await daily_task_guard(db, user_id):
        _log_skip(user_id, trigger_source, reason="task_exists_today")
        return

    ctx = await fetch_context(db, user_id)
    rule = await get_rule_for_user(db, user_id)
    rule_res = calculate(ctx, rule)

    if not rule_res["should_trigger"]:
        _log_skip(user_id, trigger_source, reason="threshold_not_met")
        return

    last_gps = ctx["last_gps"]
    parks = await find_nearby_parks(db, last_gps["lat"], last_gps["lng"], user_id)
    for i, p in enumerate(parks):
        p["index"] = i

    content = {"parks": parks}

    task = DynamicTaskLog(
        user_id=user_id,
        task_content=content,
        task_status="awaiting_selection",
        task_date=date.today(),
        created_at=datetime.utcnow(),
        expires_at=end_of_today(),
        reward_points=rule["exercise_pts"],
    )
    db.add(task)
    await db.commit()
    logger.info(f"Triggered dynamic task awaiting selection for user {user_id}")


GEOFENCE_M = 200


class TaskNotActive(Exception):
    pass


async def award_points(db: AsyncSession, user_id: str, delta: int) -> None:
    stmt = text("""
        INSERT INTO reward_log (user_id, total_points, accumulated_points, consumed_points, updated_at)
        VALUES (:u, :p, :p, 0, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
            total_points       = reward_log.total_points + excluded.total_points,
            accumulated_points = reward_log.accumulated_points + excluded.accumulated_points,
            updated_at         = CURRENT_TIMESTAMP
    """)
    await db.execute(stmt, {"u": user_id, "p": delta})


async def verify_arrival(
    db: AsyncSession, task_id: int, ulat: float, ulng: float
) -> dict:
    try:
        result = await db.execute(
            select(DynamicTaskLog)
            .where(DynamicTaskLog.task_id == task_id)
            .with_for_update()
        )
        t = result.scalar_one_or_none()
        if not t:
            raise TaskNotActive("Task not found")
        if t.task_status != "pending":
            await db.rollback()
            raise TaskNotActive("Task status is not pending")
        if t.target_lat is None or t.target_lng is None:
            await db.rollback()
            return {"passed": False, "distance_m": -1, "threshold_m": GEOFENCE_M}

        d = haversine(ulat, ulng, float(t.target_lat), float(t.target_lng))
        if d <= GEOFENCE_M:
            t.task_status = "completed"
            t.completed_at = datetime.utcnow()
            await award_points(db, t.user_id, t.reward_points)
            await db.commit()
            return {"passed": True, "distance_m": round(d)}
        else:
            await db.rollback()
            return {"passed": False, "distance_m": round(d), "threshold_m": GEOFENCE_M}
    except Exception as e:
        await db.rollback()
        raise e


FLOWER_THRESHOLD = 500


async def get_flower_state(db: AsyncSession, user_id: str) -> dict:
    stmt = select(RewardLog.accumulated_points).where(RewardLog.user_id == user_id)
    pts = await db.scalar(stmt) or 0
    return {
        "bloomed_count": pts // FLOWER_THRESHOLD,
        "current_progress": pts % FLOWER_THRESHOLD,
        "seed_active": True,
    }
