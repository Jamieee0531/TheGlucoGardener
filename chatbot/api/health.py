"""Health API — glucose readings, meal counts, body check-in, meal logging."""
import tempfile
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel

from chatbot.api.db import get_conn
from chatbot.agents.triage import analyze_image

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


class BodyCheckinRequest(BaseModel):
    user_id: str
    waist_cm: float
    weight_kg: float


class BodyCheckinResponse(BaseModel):
    message: str
    already_done: bool
    reward_points: int


class TaskStatusResponse(BaseModel):
    body_checkin_done: bool
    breakfast_done: bool
    lunch_done: bool
    dinner_done: bool


class LogMealResponse(BaseModel):
    message: str
    success: bool
    food_name: Optional[str] = None
    gi_level: Optional[str] = None
    total_calories: Optional[float] = None
    reward_points: int = 0


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


@router.get("/task-status", response_model=TaskStatusResponse)
async def task_status(user_id: str) -> TaskStatusResponse:
    conn = get_conn()
    try:
        cur = conn.cursor()
        week_period = _current_week_period()
        today = datetime.now().strftime("%Y-%m-%d")

        # Check weekly body check-in
        cur.execute(
            """SELECT task_id FROM routine_task_log
               WHERE user_id = %s AND task_type = 'weekly_waist'
               AND period = %s AND task_status = 'completed'""",
            (user_id, week_period),
        )
        body_done = cur.fetchone() is not None

        # Check today's meals
        meal_status = {}
        for meal in ["breakfast", "lunch", "dinner"]:
            cur.execute(
                """SELECT task_id FROM routine_task_log
                   WHERE user_id = %s AND task_type = %s
                   AND period = %s AND task_status = 'completed'""",
                (user_id, meal, today),
            )
            meal_status[meal] = cur.fetchone() is not None

        return TaskStatusResponse(
            body_checkin_done=body_done,
            breakfast_done=meal_status["breakfast"],
            lunch_done=meal_status["lunch"],
            dinner_done=meal_status["dinner"],
        )
    finally:
        conn.close()


def _current_week_period() -> str:
    now = datetime.now()
    week_num = now.isocalendar()[1]
    return f"{now.year}-week{week_num}"


@router.post("/body-checkin", response_model=BodyCheckinResponse)
async def body_checkin(req: BodyCheckinRequest) -> BodyCheckinResponse:
    conn = get_conn()
    try:
        cur = conn.cursor()
        period = _current_week_period()

        # Check if already done this week
        cur.execute(
            """SELECT task_id FROM routine_task_log
               WHERE user_id = %s AND task_type = 'weekly_waist'
               AND period = %s AND task_status = 'completed'""",
            (req.user_id, period),
        )
        if cur.fetchone():
            return BodyCheckinResponse(
                message="Already completed this week",
                already_done=True,
                reward_points=0,
            )

        # Update users table with new waist and weight
        cur.execute(
            """UPDATE users SET waist_cm = %s, weight_kg = %s, updated_at = NOW()
               WHERE user_id = %s""",
            (req.waist_cm, req.weight_kg, req.user_id),
        )

        # Insert completed task record
        reward = 20
        cur.execute(
            """INSERT INTO routine_task_log
               (user_id, task_type, period, task_status, created_at, completed_at, reward_points)
               VALUES (%s, 'weekly_waist', %s, 'completed', NOW(), NOW(), %s)""",
            (req.user_id, period, reward),
        )

        # Add reward points
        cur.execute(
            """UPDATE reward_log
               SET accumulated_points = accumulated_points + %s,
                   total_points = total_points + %s,
                   updated_at = NOW()
               WHERE user_id = %s""",
            (reward, reward, req.user_id),
        )

        conn.commit()
        return BodyCheckinResponse(
            message="Body check-in completed",
            already_done=False,
            reward_points=reward,
        )
    finally:
        conn.close()


@router.post("/reset-tasks")
async def reset_tasks(user_id: str = Form(...)):
    conn = get_conn()
    try:
        cur = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        week_period = _current_week_period()

        # Sum up points to deduct
        cur.execute(
            """SELECT COALESCE(SUM(reward_points), 0) FROM routine_task_log
               WHERE user_id = %s AND (
                 (task_type = 'weekly_waist' AND period = %s)
                 OR (task_type IN ('breakfast','lunch','dinner') AND period = %s)
               ) AND task_status = 'completed'""",
            (user_id, week_period, today),
        )
        points_to_deduct = cur.fetchone()[0]

        # Delete routine tasks (this week's body check-in + today's meals)
        cur.execute(
            """DELETE FROM routine_task_log
               WHERE user_id = %s AND (
                 (task_type = 'weekly_waist' AND period = %s)
                 OR (task_type IN ('breakfast','lunch','dinner') AND period = %s)
               )""",
            (user_id, week_period, today),
        )

        # Delete today's food log
        cur.execute(
            """DELETE FROM user_food_log
               WHERE user_id = %s AND recorded_at::date = %s""",
            (user_id, today),
        )

        # Deduct points
        if points_to_deduct > 0:
            cur.execute(
                """UPDATE reward_log
                   SET accumulated_points = GREATEST(accumulated_points - %s, 0),
                       total_points = GREATEST(total_points - %s, 0),
                       updated_at = NOW()
                   WHERE user_id = %s""",
                (points_to_deduct, points_to_deduct, user_id),
            )

        conn.commit()
        return {"message": "Reset complete", "points_deducted": int(points_to_deduct)}
    finally:
        conn.close()


def _auto_meal_type() -> str:
    """Determine meal type from current hour."""
    hour = datetime.now().hour
    if hour < 11:
        return "breakfast"
    if hour < 15:
        return "lunch"
    return "dinner"


@router.post("/log-meal", response_model=LogMealResponse)
async def log_meal(
    user_id: str = Form(...),
    meal_type: Optional[str] = Form(None),
    image: UploadFile = File(...),
):
    # Save uploaded image to temp file
    content = await image.read()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
    tmp.write(content)
    tmp.close()

    # Call Vision Agent
    result = analyze_image(tmp.name)

    if result is None:
        return LogMealResponse(
            message="Image analysis timed out. Please try again.",
            success=False,
        )

    if result.is_error or not result.structured_output:
        return LogMealResponse(
            message=f"Could not analyse image: {result.error or 'unknown error'}",
            success=False,
        )

    output = result.structured_output.model_dump()

    # Check if it's a food image
    if output.get("scene_type") != "FOOD":
        return LogMealResponse(
            message="This doesn't look like a food photo. Please upload a meal photo.",
            success=False,
        )

    food_name = output.get("food_name", "Unknown")
    gi_level = output.get("gi_level", "medium")
    total_calories = output.get("total_calories", 0)
    meal = meal_type or _auto_meal_type()
    today = datetime.now().strftime("%Y-%m-%d")
    reward = 20

    conn = get_conn()
    try:
        cur = conn.cursor()

        # Check if this meal already logged today
        cur.execute(
            """SELECT task_id FROM routine_task_log
               WHERE user_id = %s AND task_type = %s
               AND period = %s AND task_status = 'completed'""",
            (user_id, meal, today),
        )
        if cur.fetchone():
            return LogMealResponse(
                message=f"{meal.capitalize()} already logged today",
                success=False,
                food_name=food_name,
            )

        # Insert into user_food_log
        cur.execute(
            """INSERT INTO user_food_log
               (user_id, recorded_at, food_name, meal_type, gi_level, total_calories)
               VALUES (%s, NOW(), %s, %s, %s, %s)""",
            (user_id, food_name, meal, gi_level, total_calories),
        )

        # Insert routine_task_log
        cur.execute(
            """INSERT INTO routine_task_log
               (user_id, task_type, period, task_status, created_at, completed_at, reward_points)
               VALUES (%s, %s, %s, 'completed', NOW(), NOW(), %s)""",
            (user_id, meal, today, reward),
        )

        # Add reward points
        cur.execute(
            """UPDATE reward_log
               SET accumulated_points = accumulated_points + %s,
                   total_points = total_points + %s,
                   updated_at = NOW()
               WHERE user_id = %s""",
            (reward, reward, user_id),
        )

        conn.commit()
        return LogMealResponse(
            message=f"{meal.capitalize()} logged successfully!",
            success=True,
            food_name=food_name,
            gi_level=gi_level,
            total_calories=total_calories,
            reward_points=reward,
        )
    finally:
        conn.close()
