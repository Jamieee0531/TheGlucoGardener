import json as _json

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta

from task_agent.db.session import get_db
from task_agent.db.models import DynamicTaskLog, RewardLog, User, UserExerciseLog, UserCgmLog, UserHrLog
from task_agent.agent import agent_orchestrator
from task_agent.agent.graph import copy_subgraph
from task_agent.agent.context_loader import fetch_context
from task_agent.agent.rule_engine import get_rule_for_user, calculate

router = APIRouter()


def _content(task) -> dict:
    """Return task_content as dict, handling TEXT columns that come back as JSON strings."""
    c = task.task_content
    if isinstance(c, str):
        try:
            return _json.loads(c)
        except Exception:
            return {}
    return c or {}


class SelectDestinationReq(BaseModel):
    park_index: int

class ArriveReq(BaseModel):
    lat: float
    lng: float

class TriggerReq(BaseModel):
    user_id: str

class MockSyncReq(BaseModel):
    user_id: str
    calories_burned: float
    cgm_value: float
    lat: Optional[float] = 1.2838
    lng: Optional[float] = 103.8511


# --- 8.2 Dynamic exercise tasks ---

@router.get("/tasks/dynamic/active")
async def get_active_dynamic_task(user_id: str, db: AsyncSession = Depends(get_db)):
    now = datetime.utcnow()
    result = await db.execute(
        select(DynamicTaskLog).where(
            DynamicTaskLog.user_id == user_id,
            DynamicTaskLog.task_status.in_(["awaiting_selection", "photo_required", "pending"]),
            DynamicTaskLog.expires_at > now,
        )
    )
    task = result.scalar_one_or_none()

    if not task:
        return {"task": None}

    if task.task_status == "awaiting_selection":
        return {
            "task_id": task.task_id,
            "task_status": "awaiting_selection",
            "expires_at": task.expires_at.isoformat() if task.expires_at else None,
            "parks": _content(task).get("parks", [])
        }

    if task.task_status == "photo_required":
        return {
            "task_id": task.task_id,
            "task_status": "photo_required",
            "expires_at": task.expires_at.isoformat() if task.expires_at else None,
            "destination": _content(task).get("destination", {})
        }

    tc = _content(task)
    return {
        "task_id": task.task_id,
        "task_status": "pending",
        "expires_at": task.expires_at.isoformat() if task.expires_at else None,
        "task_content": tc if tc.get("title") else None,
        "destination": tc.get("destination", {})
    }


async def _run_langgraph_background(task_id: int, user_id: str, selected_park: dict, parks: list):
    """Runs LangGraph copy pipeline as an async FastAPI background task (main event loop)."""
    from task_agent.db.session import AsyncSessionLocal
    import logging as _logging
    _log = _logging.getLogger(__name__)

    async with AsyncSessionLocal() as db:
        try:
            ctx = await fetch_context(db, user_id)
            rule = await get_rule_for_user(db, user_id)
            rule_res = calculate(ctx, rule)

            state_in = {
                "user_id": user_id,
                "trigger_source": "user_selection",
                "user_profile": ctx["user_profile"],
                "calories_burned_today": ctx["calories_burned_today"],
                "avg_bg_last_2h": ctx["avg_bg_last_2h"],
                "exercise_history": ctx["exercise_history"],
                "last_gps": ctx["last_gps"],
                "rule": dict(rule) if hasattr(rule, "items") else rule,
                "rule_result": rule_res,
                "selected_park": selected_park,
                "park_candidates": parks,
            }

            final_state = await copy_subgraph.ainvoke(state_in)
            content = final_state.get("task_content") or {}
            content["destination"] = selected_park

            result = await db.execute(
                select(DynamicTaskLog).where(DynamicTaskLog.task_id == task_id)
            )
            task = result.scalar_one_or_none()
            if task:
                task.task_content = content
                await db.commit()
                _log.info(f"LangGraph copy written for task {task_id}")
        except Exception as e:
            _log.error(f"Background LangGraph failed for task {task_id}: {e}")
            try:
                result = await db.execute(
                    select(DynamicTaskLog).where(DynamicTaskLog.task_id == task_id)
                )
                task = result.scalar_one_or_none()
                if task and not _content(task).get("title"):
                    task.task_content = {
                        "destination": selected_park,
                        "title": "Time for your walk!",
                        "body": f"Head to {selected_park['name']} for a 30-minute walk.",
                        "cta": "I have arrived",
                        "_fallback": True,
                    }
                    await db.commit()
            except Exception:
                pass


@router.post("/tasks/dynamic/{task_id}/select-destination")
async def select_destination(
    task_id: int,
    req: SelectDestinationReq,
    user_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(DynamicTaskLog).where(
            DynamicTaskLog.task_id == task_id,
            DynamicTaskLog.user_id == user_id,
            DynamicTaskLog.task_status == "awaiting_selection",
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or not in awaiting_selection state")

    parks = _content(task).get("parks", [])
    if req.park_index < 0 or req.park_index >= len(parks):
        raise HTTPException(status_code=400, detail="Invalid park index")

    selected_park = parks[req.park_index]
    task.target_lat = selected_park["lat"]
    task.target_lng = selected_park["lng"]
    task.task_status = "photo_required"
    await db.commit()

    background_tasks.add_task(
        _run_langgraph_background,
        task_id=task_id,
        user_id=user_id,
        selected_park=selected_park,
        parks=parks,
    )

    return {"task_id": task_id, "status": "photo_required"}


@router.post("/tasks/dynamic/{task_id}/arrive")
async def arrive_at_destination(task_id: int, user_id: str, req: ArriveReq, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DynamicTaskLog).where(DynamicTaskLog.task_id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.user_id != user_id:
        raise HTTPException(status_code=403, detail="Task does not belong to this user")
    try:
        res = await agent_orchestrator.verify_arrival(db, task_id, req.lat, req.lng)
        if not res["passed"]:
            raise HTTPException(status_code=422, detail=res)
        return res
    except agent_orchestrator.TaskNotActive as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/tasks/dynamic/{task_id}/upload-photo")
async def upload_task_photo(
    task_id: int,
    user_id: str,
    photo: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(DynamicTaskLog).where(
            DynamicTaskLog.task_id == task_id,
            DynamicTaskLog.user_id == user_id,
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.task_status != "photo_required":
        raise HTTPException(status_code=409, detail=f"Task status is '{task.task_status}', expected 'photo_required'")

    if not photo.content_type or not photo.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image (image/*)")
    contents = await photo.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File exceeds 10MB limit")

    task.task_status = "pending"
    await db.commit()

    return {
        "task_id": task.task_id,
        "status": "pending",
        "task_content": _content(task) if _content(task).get("title") else None,
    }


@router.get("/internal/user-context/{user_id}")
async def get_user_context(user_id: str, db: AsyncSession = Depends(get_db)):
    ctx = await fetch_context(db, user_id)
    rule = await get_rule_for_user(db, user_id)
    rule_res = calculate(ctx, rule)
    return {
        "context": ctx,
        "rule": dict(rule) if hasattr(rule, "items") else rule,
        "rule_result": rule_res
    }


@router.post("/internal/agent/trigger")
async def internal_trigger(req: TriggerReq, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    await agent_orchestrator.run(db, req.user_id, "admin")
    return {"status": "triggered"}


class AwardPointsReq(BaseModel):
    user_id: str
    delta: int
    reason: Optional[str] = None


@router.post("/internal/points/award")
async def internal_award_points(req: AwardPointsReq, db: AsyncSession = Depends(get_db)):
    if req.delta <= 0:
        raise HTTPException(status_code=400, detail="delta must be a positive integer")
    result = await db.execute(select(User).where(User.user_id == req.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await agent_orchestrator.award_points(db, req.user_id, req.delta)
    await db.commit()
    reward_result = await db.execute(select(RewardLog).where(RewardLog.user_id == req.user_id))
    reward = reward_result.scalar_one_or_none()
    new_total = reward.total_points if reward else req.delta
    return {"user_id": req.user_id, "points_awarded": req.delta, "new_total": new_total}


@router.post("/internal/mock/sync-data")
async def mock_sync_data(req: MockSyncReq, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.user_id == req.user_id))
    user = result.scalar_one_or_none()
    if not user:
        db.add(User(user_id=req.user_id, name="Demo User", weight_kg=80.0, height_cm=175.0, gender="male"))
        await db.commit()

    db.add(UserExerciseLog(
        user_id=req.user_id, exercise_type="walking",
        calories_burned=req.calories_burned,
        started_at=datetime.utcnow() - timedelta(minutes=10),
        ended_at=datetime.utcnow()
    ))
    db.add(UserCgmLog(user_id=req.user_id, glucose=req.cgm_value, recorded_at=datetime.utcnow()))
    db.add(UserHrLog(
        user_id=req.user_id, heart_rate=80,
        gps_lat=req.lat, gps_lng=req.lng, recorded_at=datetime.utcnow()
    ))
    await db.commit()
    return {"status": "synced"}


@router.delete("/internal/test/reset-tasks")
async def reset_tasks_for_testing(user_id: str, db: AsyncSession = Depends(get_db)):
    from task_agent.agent.context_loader import _sgt_today_start_utc
    from sqlalchemy import delete as sql_delete
    today_start = _sgt_today_start_utc()

    # Delete today's dynamic tasks
    r = await db.execute(select(DynamicTaskLog).where(DynamicTaskLog.user_id == user_id))
    tasks = r.scalars().all()
    for t in tasks:
        await db.delete(t)

    # Clear today's seeded sensor data so calories don't accumulate across demo runs
    await db.execute(sql_delete(UserExerciseLog).where(
        UserExerciseLog.user_id == user_id,
        UserExerciseLog.started_at >= today_start,
    ))
    await db.execute(sql_delete(UserCgmLog).where(
        UserCgmLog.user_id == user_id,
        UserCgmLog.recorded_at >= today_start,
    ))
    await db.execute(sql_delete(UserHrLog).where(
        UserHrLog.user_id == user_id,
        UserHrLog.recorded_at >= today_start,
    ))

    await db.commit()
    return {"deleted_tasks": len(tasks), "sensor_data_cleared": True, "user_id": user_id}


# --- 8.3 Points and flower ---

@router.get("/points/summary")
async def get_points_summary(user_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RewardLog).where(RewardLog.user_id == user_id))
    summary = result.scalar_one_or_none()
    if not summary:
        return {"total_points": 0, "accumulated_points": 0, "consumed_points": 0}
    return {
        "total_points": summary.total_points,
        "accumulated_points": summary.accumulated_points,
        "consumed_points": summary.consumed_points
    }


@router.get("/points/flower")
async def get_points_flower(user_id: str, db: AsyncSession = Depends(get_db)):
    return await agent_orchestrator.get_flower_state(db, user_id)
