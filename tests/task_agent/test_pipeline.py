import asyncio
import io
import json
import pytest
import pytest_asyncio
from fastapi import BackgroundTasks, UploadFile
from starlette.datastructures import Headers

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from task_agent.db.models import Base, User, DynamicTaskRule

_TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
_test_engine = create_async_engine(_TEST_DB_URL)
_TestSession = async_sessionmaker(
    bind=_test_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

from task_agent.agent import agent_orchestrator
from task_agent.api.routes import (
    get_active_dynamic_task,
    select_destination,
    arrive_at_destination,
    upload_task_photo,
    get_points_summary,
    SelectDestinationReq,
    ArriveReq,
)


@pytest_asyncio.fixture
async def db():
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with _TestSession() as session:
        session.add(User(user_id="test_user_1", name="Test User", language_pref="en"))
        session.add(DynamicTaskRule(base_calorie=300, trigger_threshold=0.6, exercise_pts=50))
        await session.commit()
        yield session
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_run_pipeline(db: AsyncSession):
    print("--- 1. Admin triggers task ---")
    await agent_orchestrator.run(db, user_id="test_user_1", trigger_source="admin")

    print("--- 2. App gets active task (awaiting_selection) ---")
    active_task = await get_active_dynamic_task(user_id="test_user_1", db=db)
    print("Active Task Response:", json.dumps(active_task, indent=2))
    task_id = active_task.get("task_id")

    assert task_id, "FAIL: No task generated"
    parks = active_task.get("parks", [])
    assert parks, "FAIL: No parks in task"
    selected_park = parks[0]

    print("--- 3. User selects a park ---")
    await select_destination(
        task_id=task_id,
        req=SelectDestinationReq(park_index=0),
        user_id="test_user_1",
        background_tasks=BackgroundTasks(),
        db=db,
    )

    print("--- 4. App gets active task (photo_required) ---")
    photo_task = await get_active_dynamic_task(user_id="test_user_1", db=db)
    assert photo_task["task_status"] == "photo_required"

    print("--- 5. User uploads proof-of-intent photo ---")
    mock_photo = UploadFile(
        file=io.BytesIO(b"\xff\xd8\xff" + b"0" * 100),
        filename="proof.jpg",
        headers=Headers({"content-type": "image/jpeg"}),
    )
    await upload_task_photo(task_id=task_id, user_id="test_user_1", photo=mock_photo, db=db)

    print("--- 6. App gets active task (pending) ---")
    pending_task = await get_active_dynamic_task(user_id="test_user_1", db=db)
    assert pending_task["task_status"] == "pending"

    print(f"--- 7. User arrives at {selected_park['name']} ---")
    res = await arrive_at_destination(
        task_id=task_id,
        user_id="test_user_1",
        req=ArriveReq(lat=selected_park["lat"], lng=selected_park["lng"]),
        db=db,
    )
    assert res["passed"] is True

    print("--- 8. Check points ---")
    points = await get_points_summary(user_id="test_user_1", db=db)
    assert points["total_points"] > 0
