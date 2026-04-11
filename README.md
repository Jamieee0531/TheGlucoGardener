<p align="center">
  <img src="docs/logo.jpg" alt="GlucoGardener Logo" width="280" />
</p>

# The GlucoGardener

AI-powered proactive chronic disease management platform for diabetic patients in Singapore.

Built for the **NUS-SYNAPXE-IMDA AI Innovation Challenge 2026** — selected as a **Top 8 Finalist out of 181 teams**.

![GlucoGardener Poster](docs/AAAMedMaster_%20Executive%20Summary.png)

**Presentation slides:** [AAAMedMaster_Presentation.pdf](docs/AAAMedMaster_Presentation.pdf)

---

## What is GlucoGardener?

GlucoGardener is a multi-agent AI system that helps elderly diabetic patients manage their health through:

- **Proactive Alerts** — Predicts glucose risks (e.g., pre-exercise hypoglycemia) and sends personalised suggestions *before* problems occur
- **Health Companion Chatbot** — Multi-turn conversational AI with emotion awareness, medical Q&A, diet advice, and glucose analysis
- **Vision Agent** — Analyzes food photos, medication images, and medical reports using computer vision
- **Daily Task System** — Guided health tasks (meal logging, exercise, body check-ins) with dynamic AI-generated tasks
- **Gamification (Garden)** — Grow a virtual garden by completing health tasks, visit friends' gardens, send encouragement messages

Target users: Elderly diabetic patients in Singapore (e.g., 68-year-old Mdm Chen, a retired teacher living alone with Type 2 Diabetes).

---

## Architecture

### Multi-Agent System

```
                  ┌─ Chatbot Agent (conversation) ──→ Vision Agent (image analysis)
                  │                                    [direct import]
                  │
  Shared DB ←────┼─ Task Agent (daily tasks) ──→ Vision Agent (image analysis)
  (PostgreSQL)    │   User uploads meal photos → Vision analyzes → nutrition data saved
                  │
                  └─ Alert Agent (proactive alerts)
                      Reads glucose/heart rate data, triggers soft/hard alerts
                      Pipeline: Investigator → Reflector → Communicator (SEA-LION)
```

### Services

| Service | Port | Description |
|---------|------|-------------|
| Frontend (Next.js) | 3000 | User interface |
| Chatbot API (FastAPI) | 8080 | Chat, Garden, Users, Health APIs |
| Gateway (FastAPI) | 8000 | Alert telemetry, triage, interventions |
| Task Agent (FastAPI) | 8001 | Dynamic task generation (nearby parks, personalised exercises) |
| Redis | 6379 | Message queue for Celery |
| Celery Worker | — | Alert Agent background processing |

### Chatbot Flow (LangGraph)

```
User Input (text / image / voice)
    │
input_node       ← image → Vision Agent; voice → MeraLion STT
    │
glucose_reader   ← fetches weekly glucose & diet history
    │
triage_node      ← keyword pre-classification + LLM intent routing
    │                + background RAG prefetch for medical queries
    │
    ├── Expert Agent     ← medical Q&A, diet advice, glucose analysis
    ├── Companion Agent  ← emotional support, daily conversation
    ├── Hybrid Agent     ← mixed intent
    └── Crisis Agent     ← emergency situations
    │
history_update   ← persist conversation to PostgreSQL
```

### Vision Agent Pipeline (LangGraph)

```
[Image Input(s)]
     │
[image_intake]        Receive image(s), validate, convert to base64
     │
[scene_classifier]    Classify: FOOD / MEDICATION / REPORT / UNKNOWN
     │
     ├── FOOD       → [food_analyzer]       Identify dishes, estimate nutrition
     ├── MEDICATION → [medication_reader]    Extract drug name, dosage, frequency
     ├── REPORT     → [report_digitizer]     Extract lab indicators (HbA1c, glucose)
     └── UNKNOWN    → [rejection_handler]    Reject non-target images
     │
[output_formatter]    Validate with Pydantic → unified JSON output
```

---

## Features

### Frontend Pages

| Page | Route | Description |
|------|-------|-------------|
| **Login** | `/login` | User selection with avatar display |
| **Onboarding** | `/onboarding` | New user setup wizard |
| **Home** | `/` | Health snapshot (BMI, meals, glucose chart), soft/hard alert modals |
| **Chat** | `/chat` | Streaming AI conversation with voice input, image upload |
| **Warm Up** | `/warmup` | Daily exercise check-in — confirms or updates exercise plan |
| **Task** | `/task` | Daily health tasks (meal logging with MiniChat, body check-in, dynamic AI tasks) |
| **Garden** | `/garden` | Virtual garden, friend rankings, message board |
| **Settings** | `/setting` | User profile, emergency contacts, known places, exercise patterns |
| **Soft Alert** | `/soft-alert` | Proactive glucose risk alert demo |
| **Hard Alert** | `/hard-alert` | Emergency alert demo |
| **Demo Console** | `/demo` | Alert Agent demo scenarios |

### API Endpoints (Chatbot API — Port 8080)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat/message` | Send message, get full response |
| POST | `/chat/stream` | Send message, get streaming SSE response |
| POST | `/chat/task-hint` | Get AI hint for a task |
| GET | `/users/list` | List all users |
| GET | `/users/{user_id}` | Get user profile |
| PUT | `/users/{user_id}` | Update user profile |
| GET | `/users/{user_id}/exercise-patterns` | Get weekly exercise patterns |
| POST | `/users/{user_id}/exercise-patterns` | Update exercise patterns |
| GET | `/users/{user_id}/emergency-contacts` | Get emergency contacts |
| POST | `/users/{user_id}/emergency-contacts` | Update emergency contacts |
| GET | `/users/{user_id}/known-places` | Get known places |
| POST | `/users/{user_id}/known-places` | Update known places |
| GET | `/garden/my` | Get user's garden points |
| GET | `/garden/friends` | Get friends list with points |
| POST | `/garden/water` | Water a friend's garden |
| GET | `/health/glucose` | Get glucose readings |
| GET | `/health/meals-today` | Get today's meal count |
| GET | `/health/daily-tasks` | Get daily task status |
| GET | `/health/task-status` | Get task completion status |
| GET | `/health/recent-exercise` | Get recent exercise count |
| POST | `/health/log-exercise` | Log an exercise session |
| POST | `/health/log-meal` | Log a meal (with Vision Agent analysis) |
| POST | `/health/body-checkin` | Log body measurements |
| POST | `/health/reset-tasks` | Reset daily tasks |

All chat endpoints accept `FormData` with fields: `user_id`, `session_id`, `text`, `image`, `audio`.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Next.js 16, React 19, Tailwind CSS 4 |
| **Backend** | Python 3.10+, FastAPI, LangGraph |
| **AI — Text** | SEA-LION (AISG) |
| **AI — Vision** | Gemini 2.5 Flash |
| **AI — Voice** | MeraLion (AISG) |
| **AI — Triage** | OpenAI GPT-4o-mini |
| **AI — RAG** | ChromaDB + BM25 hybrid, Jina AI embedding + reranker |
| **Database** | PostgreSQL (Huawei Cloud) |
| **Task Queue** | Redis + Celery |
| **Validation** | Pydantic v2 |
| **Testing** | pytest (171 tests, 99%+ coverage for Vision Agent) |

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Redis (for Alert Agent)
- PostgreSQL database

### 1. Clone and Setup

```bash
git clone https://github.com/Jamieee0531/TheGlucoGardener.git
cd SG_INNOVATION

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
.venv/bin/python3 -m pip install -r requirements.txt

# Install frontend dependencies
cd frontend && npm install && cd ..
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys (see Environment Variables below)
```

### 3. Start Services

```bash
# Terminal 1: Chatbot API
source .venv/bin/activate
uvicorn chatbot.api.main:api --reload --port 8080

# Terminal 2: Frontend
cd frontend && npm run dev
# Open http://localhost:3000

# Terminal 3: Gateway (Alert Agent)
source .venv/bin/activate
uvicorn gateway.app:app --reload --port 8000

# Terminal 4: Task Agent
source .venv/bin/activate
uvicorn task_agent.main:app --reload --port 8001

# Terminal 5: Redis
redis-server

# Terminal 6: Celery Worker (Alert Agent)
source .venv/bin/activate
celery -A pipeline.celery_app worker --loglevel=info
```

### Deployment

For cloud deployment, set these environment variables on your hosting platform (e.g., Vercel for frontend):

```
NEXT_PUBLIC_API_BASE=https://your-backend-url.com
NEXT_PUBLIC_GATEWAY_URL=https://your-gateway-url.com
NEXT_PUBLIC_TASK_AGENT_URL=https://your-task-agent-url.com
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PG_HOST` | Yes | PostgreSQL host |
| `PG_PORT` | Yes | PostgreSQL port (default: 5432) |
| `PG_USER` | Yes | PostgreSQL username |
| `PG_PASSWORD` | Yes | PostgreSQL password |
| `PG_DB` | Yes | PostgreSQL database name |
| `GEMINI_API_KEY` | Yes | Google Gemini API key (vision + triage) |
| `SEALION_API_KEY` | Yes | SEA-LION API key (text generation) |
| `OPENAI_API_KEY` | Yes | OpenAI API key (intent classification) |
| `MERALION_API_KEY` | Yes | MeraLion API key (voice transcription) |
| `JINA_API_KEY` | Yes | Jina AI API key (RAG embedding + reranking) |
| `GOOGLE_MAPS_API_KEY` | Yes | Google Maps API key (nearby park search) |
| `VLM_PROVIDER` | No | VLM provider: `gemini`, `sealion`, `mock` (default: `gemini`) |
| `DEMO_MODE` | No | Enable demo reset endpoints (default: `false`) |

---

## Project Structure

```
SG_INNOVATION/
├── chatbot/                          # Health Companion Chatbot
│   ├── api/
│   │   ├── main.py                   # FastAPI app + chat endpoints
│   │   ├── garden.py                 # Garden endpoints
│   │   ├── health.py                 # Health endpoints (meals, exercise, glucose)
│   │   ├── users.py                  # User profile endpoints
│   │   └── db.py                     # PostgreSQL connection
│   ├── agents/                       # triage, expert, companion, glucose_reader
│   ├── graph/builder.py              # LangGraph graph definition
│   ├── state/chat_state.py           # ChatState (TypedDict)
│   ├── utils/                        # llm_factory, memory, meralion
│   ├── config/settings.py            # Environment config
│   └── memory/                       # Long-term storage + RAG (ChromaDB)
│
├── src/vision_agent/                 # Vision Agent
│   ├── agent.py                      # Public API: VisionAgent.analyze()
│   ├── graph.py                      # LangGraph state graph
│   ├── nodes/                        # Pipeline nodes (7 nodes)
│   ├── prompts/                      # SG-optimized prompt templates
│   ├── schemas/outputs.py            # Pydantic v2 output models
│   └── llm/                          # VLM interface (Gemini, SEA-LION, Mock)
│
├── gateway/                          # Alert Gateway (Julia)
│   └── app.py                        # FastAPI — telemetry, triage, interventions
│
├── alert_agent/                      # Alert Agent (Julia)
│   └── ...                           # Investigator → Reflector → Communicator
│
├── pipeline/                         # Celery pipeline for Alert Agent
│   └── celery_app.py
│
├── task_agent/                       # Task Agent (Chayi)
│   └── main.py                       # FastAPI — dynamic task generation
│
├── frontend/                         # Next.js Frontend
│   └── src/
│       ├── app/                      # Pages (home, chat, task, garden, warmup, etc.)
│       ├── components/               # TopBar, SugarChart, MiniChat
│       └── lib/                      # API helpers, i18n, auth, config
│
├── tests/                            # Vision Agent tests (171 tests)
├── config.py                         # Shared config (Gateway)
├── requirements.txt                  # Python dependencies
└── LICENSE                           # MIT License
```

---

## Team

| Member | Role |
|--------|------|
| Jamie ([@Jamieee0531](https://github.com/Jamieee0531)) | Vision Agent, Chatbot Integration, Frontend |
| Bailey ([@baileybei](https://github.com/baileybei)) | Health Companion Chatbot (RAG, triage, voice) |
| Chayi ([@Verse-Founder](https://github.com/Verse-Founder)) | Task Agent (dynamic task generation) |
| Julia ([@juliawangjiayu](https://github.com/juliawangjiayu)) | Alert Agent, Gateway, Program Leader |
| Ruiyu ([@Ruiyuyu-7](https://github.com/Ruiyuyu-7)) | UI/UX Design, Game & Interaction Design |
| Congrong ([@Douliciouss](https://github.com/Douliciouss)) | Business Model, Data Analysis, Demo & Presentation |

## License

[MIT License](LICENSE)
