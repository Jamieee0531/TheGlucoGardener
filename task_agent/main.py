"""
task_agent/main.py

FastAPI entry point for the Task Agent service (port 8001).

Usage:
    uvicorn task_agent.main:app --reload --port 8001
"""
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from task_agent.api.routes import router
from task_agent.db.session import async_engine
from task_agent.db.models import Base


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Create tables on startup (idempotent — safe to run every time)
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="Task Agent API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "task_agent"}
