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
from chatbot.utils.llm_factory import set_token_callback, clear_token_callback, call_sealion, call_sealion_with_history_stream
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
    allow_origins=["*"],
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
    mode: Optional[str] = Form(None),
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

    # ── Task mode: bypass LangGraph, use concise prompt ──────
    if mode == "task":
        _image_paths = state.get("image_paths", [])
        _audio_path  = state.get("audio_path", "")

        def run_task():
            set_token_callback(token_cb)
            transcribed = ""
            try:
                # ── ASR: transcribe audio if present ────────────
                if _audio_path:
                    from chatbot.utils.meralion import process_voice_input
                    asr_result  = process_voice_input(_audio_path)
                    transcribed = asr_result.get("transcribed_text", "")

                # ── VLM: analyse image if present ────────────────
                food_context = ""
                if _image_paths:
                    from chatbot.agents.triage import analyze_image
                    result = analyze_image(_image_paths[0])
                    if result and not result.is_error and result.structured_output:
                        food = result.structured_output
                        food_name = food.get("food_name") if isinstance(food, dict) else food.food_name
                        calories  = food.get("total_calories") if isinstance(food, dict) else food.total_calories
                        gi        = food.get("gi_level") if isinstance(food, dict) else food.gi_level
                        food_context = f"\n[Food identified: {food_name}, ~{int(calories)} kcal, {gi} GI]"

                # ── Detect language from transcription or text ───
                user_text = transcribed or text or ""
                import re as _re
                cn = len(_re.findall(r'[\u4e00-\u9fff]', user_text))
                en = len(_re.findall(r'[a-zA-Z]', user_text))
                reply_lang = "Chinese" if cn >= en else "English"

                task_system = (
                    f"You are a warm, chill health buddy embedded in a diabetes management app in Singapore.\n"
                    f"Reply ENTIRELY in {reply_lang}. Do not mix languages.\n"
                    f"The user is logging a meal or asking about food/exercise from the task screen.\n"
                    f"Reply in 1-2 sentences MAX. Be direct and friendly — like a knowledgeable friend texting.\n"
                    f"If food info is provided in [Food identified:...], use that as the basis for your response.\n"
                    f"Comment on whether the food is suitable for a diabetic, and suggest a local swap if needed.\n"
                    f"If the user asks about exercise, give a quick yes/no with one specific suggestion.\n"
                    f"No disclaimers. No bullet points. No 'consult your doctor'."
                )

                user_content = user_text + food_context
                history = [{"role": "user", "content": user_content}]
                call_sealion_with_history_stream(task_system, history)
                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    {"__done__": True, "transcribed": transcribed},
                )
            except Exception as e:
                loop.call_soon_threadsafe(queue.put_nowait, {"__error__": str(e)})
            finally:
                clear_token_callback()

        threading.Thread(target=run_task, daemon=True).start()

        async def task_event_generator():
            while True:
                item = await queue.get()
                if isinstance(item, str):
                    yield f"data: {json.dumps({'type': 'token', 'token': item})}\n\n"
                elif isinstance(item, dict):
                    if "__done__" in item:
                        done_payload = {
                            "type": "done",
                            "session_id": session_id,
                            "agent_type": "companion",
                            "reply": "",
                            "transcribed_text": item.get("transcribed", ""),
                        }
                        yield f"data: {json.dumps(done_payload)}\n\n"
                        break
                    elif "__error__" in item:
                        yield f"data: {json.dumps({'type': 'error', 'message': item['__error__']})}\n\n"
                        break

        return StreamingResponse(
            task_event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

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
                    if input_mode == "voice":
                        done_data["transcribed_text"] = result.get("transcribed_text") or ""
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


# ── Mock user health profile (replace with DB lookup later) ─────
_MOCK_PROFILE = {
    "name": "Marcus",
    "age": 58,
    "condition": "Type 2 Diabetes",
    "recent_glucose": "6.8 mmol/L (stable, measured 2 h ago)",
    "last_exercise": "2 days ago — 30 min walk",
    "medications": "Metformin 500 mg twice daily",
    "dietary_focus": "low GI, watching sodium",
    "hba1c": "7.2% (checked 2 months ago)",
}


@api.post("/chat/task-hint")
async def task_hint(
    user_id: str = Form(...),
    task_type: str = Form(...),   # "exercise" or "diet"
    question: str = Form(...),
):
    p = _MOCK_PROFILE

    if task_type == "exercise":
        system = (
            f"You are a chill, warm health buddy for {p['name']}, {p['age']}, {p['condition']} in Singapore.\n"
            f"Health snapshot: glucose {p['recent_glucose']}, last exercise {p['last_exercise']}, "
            f"on {p['medications']}.\n"
            "Reply in 1-2 sentences ONLY. Be direct and warm — like a knowledgeable friend texting, not a doctor.\n"
            "If suggesting alternatives, be specific and local (e.g. 'brisk walk at a nearby park', not 'light exercise').\n"
            "No disclaimers. No bullet points. No 'consult your doctor'."
        )
    else:  # diet
        system = (
            f"You are a chill, warm health buddy for {p['name']}, {p['age']}, {p['condition']} in Singapore.\n"
            f"Health snapshot: glucose {p['recent_glucose']}, dietary focus: {p['dietary_focus']}.\n"
            "Reply in 1-2 sentences ONLY. Be direct and warm — like a friend who knows Singapore food.\n"
            "Reference local food naturally. If something's not ideal, suggest a konkrete local swap.\n"
            "No disclaimers. No bullet points. No 'consult your doctor'."
        )

    loop = asyncio.get_event_loop()
    hint = await loop.run_in_executor(
        None, lambda: call_sealion(system, question)
    )
    return {"hint": hint}
