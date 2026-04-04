"""
chatbot/api/main.py
FastAPI entry point — POST /chat/message and POST /chat/stream endpoints.

Usage:
    uvicorn chatbot.api.main:app --reload
"""
import asyncio
import json
import threading
import uuid
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from chatbot.graph.builder import app as graph_app
from chatbot.utils.llm_factory import set_token_callback, clear_token_callback
from chatbot.memory.rag.retriever import get_retriever
from chatbot.api.garden import router as garden_router
from chatbot.api.users import router as users_router
from chatbot.api.health import router as health_router

# ── FastAPI app ──────────────────────────────────────────────────
api = FastAPI(title="Health Companion Chatbot", version="0.1.0")


@api.on_event("startup")
async def _warmup():
    """预热 RAG：启动时加载 embedding 模型 + 建索引，避免首次请求延迟。"""
    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: get_retriever()._init())

api.include_router(garden_router)
api.include_router(users_router)
api.include_router(health_router)

api.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Response schema ──────────────────────────────────────────────
class ChatResponse(BaseModel):
    session_id: str
    reply: str
    agent_type: str  # "companion" | "expert" | "crisis"
    transcribed_text: Optional[str] = None  # voice input transcription


def _intent_to_agent_type(intent: str) -> str:
    if intent == "medical":
        return "expert"
    if intent == "crisis":
        return "crisis"
    return "companion"


async def _save_upload(upload: UploadFile, suffix: str) -> str:
    """Save an uploaded file to a temp path and return the path string."""
    content = await upload.read()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(content)
    tmp.close()
    return tmp.name


@api.post("/chat/message", response_model=ChatResponse)
async def chat_message(
    user_id: str = Form(...),
    session_id: Optional[str] = Form(None),
    text: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None),
):
    # ── Normalise empty uploads (Swagger sends "string" placeholder) ─
    if image and not image.filename:
        image = None
    if audio and not audio.filename:
        audio = None

    # ── Session: auto-create if first message ────────────────
    if not session_id:
        session_id = uuid.uuid4().hex

    # ── Determine input mode ─────────────────────────────────
    input_mode = "voice" if audio else "text"

    # ── Build initial state ──────────────────────────────────
    # Note: history is managed by LangGraph's checkpointer (keyed on
    # thread_id = session_id), not via this field. We pass [] here;
    # the graph reads persisted history from the checkpointer automatically.
    state = {
        "user_input": text or "",
        "input_mode": input_mode,
        "chat_mode": "personal",
        "user_id": user_id,
        "history": [],
        "user_profile": {},
    }

    # ── Handle audio upload ──────────────────────────────────
    # Browser MediaRecorder sends WebM; save with original extension
    # so downstream ASR can detect format from content, not filename.
    if audio:
        ext = Path(audio.filename).suffix if audio.filename else ".webm"
        audio_path = await _save_upload(audio, suffix=ext)
        state["audio_path"] = audio_path

    # ── Handle image upload ──────────────────────────────────
    if image:
        image_path = await _save_upload(image, suffix=".jpg")
        state["image_paths"] = [image_path]

    # ── Invoke LangGraph ─────────────────────────────────────
    config = {"configurable": {"thread_id": session_id}}
    result = graph_app.invoke(state, config=config)

    # ── Extract response ─────────────────────────────────────
    reply = result.get("response", "")
    intent = result.get("intent", "companion")
    agent_type = _intent_to_agent_type(intent)

    transcribed = result.get("transcribed_text") if input_mode == "voice" else None

    return ChatResponse(
        session_id=session_id,
        reply=reply,
        agent_type=agent_type,
        transcribed_text=transcribed,
    )


@api.post("/chat/stream")
async def chat_stream(
    user_id: str = Form(...),
    session_id: Optional[str] = Form(None),
    text: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None),
):
    # ── Normalise empty uploads ───────────────────────────────
    if image and not image.filename:
        image = None
    if audio and not audio.filename:
        audio = None

    # ── Session: auto-create if first message ────────────────
    if not session_id:
        session_id = uuid.uuid4().hex

    # ── Determine input mode ─────────────────────────────────
    input_mode = "voice" if audio else "text"

    # ── Build initial state ──────────────────────────────────
    state = {
        "user_input": text or "",
        "input_mode": input_mode,
        "chat_mode": "personal",
        "user_id": user_id,
        "history": [],
        "user_profile": {},
    }

    # ── Handle audio upload ──────────────────────────────────
    if audio:
        ext = Path(audio.filename).suffix if audio.filename else ".webm"
        audio_path = await _save_upload(audio, suffix=ext)
        state["audio_path"] = audio_path

    # ── Handle image upload ──────────────────────────────────
    if image:
        image_path = await _save_upload(image, suffix=".jpg")
        state["image_paths"] = [image_path]

    # ── Set up streaming queue and callback ──────────────────
    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def token_cb(token: str) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, token)

    # ── Run the graph in a background thread ─────────────────
    config = {"configurable": {"thread_id": session_id}}

    def run_graph():
        # Set callback on THIS thread (threading.local is per-thread)
        set_token_callback(token_cb)
        try:
            result = graph_app.invoke(state, config=config)
            loop.call_soon_threadsafe(
                queue.put_nowait, {"__done__": True, "result": result}
            )
        except Exception as e:
            loop.call_soon_threadsafe(
                queue.put_nowait, {"__error__": str(e)}
            )
        finally:
            clear_token_callback()

    t = threading.Thread(target=run_graph, daemon=True)
    t.start()

    # ── Async generator that yields SSE events ───────────────
    async def event_generator():
        while True:
            item = await queue.get()
            if isinstance(item, str):
                payload = json.dumps({"type": "token", "token": item})
                yield f"data: {payload}\n\n"
            elif isinstance(item, dict):
                if "__done__" in item:
                    result = item["result"]
                    intent = result.get("intent", "companion")
                    agent_type = _intent_to_agent_type(intent)
                    done_data = {
                        "type": "done",
                        "session_id": session_id,
                        "agent_type": agent_type,
                        "reply": result.get("response", ""),
                    }
                    if input_mode == "voice" and result.get("transcribed_text"):
                        done_data["transcribed_text"] = result["transcribed_text"]
                    payload = json.dumps(done_data)
                    yield f"data: {payload}\n\n"
                    break
                elif "__error__" in item:
                    payload = json.dumps({
                        "type": "error",
                        "message": item["__error__"],
                    })
                    yield f"data: {payload}\n\n"
                    break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
