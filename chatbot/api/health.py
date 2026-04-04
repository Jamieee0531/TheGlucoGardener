"""Health API — glucose readings, meal counts."""
from datetime import datetime, timedelta

from fastapi import APIRouter
from pydantic import BaseModel

from chatbot.api.db import get_conn

router = APIRouter(prefix="/health", tags=["health"])


class GlucoseReading(BaseModel):
    recorded_at: str
    glucose: float


class GlucoseResponse(BaseModel):
    readings: list[GlucoseReading]


class MealsTodayResponse(BaseModel):
    count: int
    total: int


class DailyTasksResponse(BaseModel):
    completed: int
    total: int


@router.get("/glucose", response_model=GlucoseResponse)
async def glucose_readings(user_id: str, hours: int = 24) -> GlucoseResponse:
    conn = get_conn()
    try:
        cur = conn.cursor()
        since = datetime.now() - timedelta(hours=hours)
        cur.execute(
            """SELECT recorded_at, glucose FROM user_cgm_log
               WHERE user_id = %s AND recorded_at >= %s
               ORDER BY recorded_at""",
            (user_id, since),
        )
        readings = [
            GlucoseReading(
                recorded_at=r[0].isoformat(),
                glucose=float(r[1]),
            )
            for r in cur.fetchall()
        ]
        return GlucoseResponse(readings=readings)
    finally:
        conn.close()


@router.get("/meals-today", response_model=MealsTodayResponse)
async def meals_today(user_id: str) -> MealsTodayResponse:
    conn = get_conn()
    try:
        cur = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        cur.execute(
            """SELECT COUNT(DISTINCT meal_type) FROM user_food_log
               WHERE user_id = %s AND recorded_at::date = %s""",
            (user_id, today),
        )
        count = cur.fetchone()[0]
        return MealsTodayResponse(count=count, total=3)
    finally:
        conn.close()


@router.get("/daily-tasks", response_model=DailyTasksResponse)
async def daily_tasks(user_id: str) -> DailyTasksResponse:
    conn = get_conn()
    try:
        cur = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        cur.execute(
            """SELECT COUNT(*) FROM routine_task_log
               WHERE user_id = %s AND task_status = 'completed'
               AND created_at::date = %s""",
            (user_id, today),
        )
        completed = cur.fetchone()[0]
        return DailyTasksResponse(completed=completed, total=4)
    finally:
        conn.close()
