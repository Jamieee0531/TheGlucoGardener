# TheGlucoGardener 本地运行指南

## 架构总览

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Frontend    │────▶│  Chatbot API     │────▶│  PostgreSQL      │
│  Next.js     │     │  FastAPI :8080   │     │  (云端，见 .env) │
│  :3000       │     └──────────────────┘     └──────────────────┘
│              │                                       ▲
│              │     ┌──────────────────┐              │
│              │────▶│  Gateway API     │──────────────┘
│              │     │  FastAPI :8000   │
└─────────────┘     └───────┬──────────┘
                            │ dispatch task via Celery
                            ▼
                    ┌──────────────────┐     ┌──────────────────┐
                    │  Redis           │────▶│  Alert Agent     │
                    │  :6379           │     │  Celery Worker   │
                    └──────────────────┘     └──────────────────┘
```

| 服务 | 端口 | 职责 |
|---|---|---|
| **Frontend** (Next.js) | 3000 | 用户界面、Demo Console |
| **Chatbot API** (FastAPI) | 8080 | 聊天、花园、用户资料、血糖查询、餐食记录 |
| **Gateway API** (FastAPI) | 8000 | 遥测数据接收、触发判定、干预记录查询 |
| **Redis** | 6379 | Celery 消息队列（Alert Agent 的任务通道） |
| **Alert Agent** (Celery Worker) | — | LangGraph 异步推理：Investigator → Reflector → Communicator |
| **PostgreSQL** | 5432 | 数据库（已云端部署，连接信息在 `.env`） |

---

## 前置条件

- **Node.js** >= 18
- **Python** >= 3.11
- **Redis**（macOS: `brew install redis`）
- 项目根目录有 `.env` 文件（数据库、API Key 等）
- 项目根目录有 `config.py`（Python 后端共享配置，读取 `.env`）

---

## 首次设置（只需做一次）

### 1. 前端依赖

```bash
cd frontend
npm install
cd ..
```

### 2. Python 虚拟环境 + 后端依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> 也可以用 `make install`，效果一样。

---

## 启动服务

需要多个终端窗口（推荐用 VSCode 的 Split Terminal）。

**每个 Python 终端都要先激活虚拟环境：**
```bash
cd /path/to/TheGlucoGardener
source .venv/bin/activate
```

### 终端 1 — Redis

```bash
redis-server
```

验证：另开终端跑 `redis-cli ping`，返回 `PONG` 即成功。

> 也可以后台运行：`brew services start redis`

### 终端 2 — Gateway API (port 8000)


```bash
source .venv/bin/activate
uvicorn gateway.main:app --host 0.0.0.0 --port 8000 --reload
```

验证：`http://localhost:8000/health` → `{"status":"ok"}`

### 终端 3 — Chatbot API (port 8080)

```bash
source .venv/bin/activate
uvicorn chatbot.api.main:api --host 0.0.0.0 --port 8080 --reload
```

> 注意：chatbot 的 FastAPI 实例是 `api` 不是 `app`。

验证：`http://localhost:8080/docs` → 看到 Swagger UI

### 终端 4 — Frontend (port 3000)

```bash
cd frontend
npm run dev
```

验证：`http://localhost:3000` → 看到登录页面

### 终端 5（可选）— Alert Agent (Celery Worker)

仅软预警需要。

```bash
source .venv/bin/activate
celery -A alert_agent.main worker --loglevel=info
```

---

## 按需启动（不用每次全开）

| 测试目的 | 需要启动的服务 |
|---|---|
| 只看前端 UI / 页面布局 | Frontend |
| 聊天 / 花园 / 用户资料 | Frontend + Chatbot API |
| Demo Console + ���预警 | Frontend + Gateway API |
| Demo Console + 软预警 | Frontend + Gateway API + Redis + Alert Agent |
| 完整联调 | 全部 5 个 |

---

## Demo Console 测试流程

1. `http://localhost:3000` → 登录 → 汉堡菜单 → **Demo Console**
2. 选一个 Scenario → 点 **Play All**
3. 右侧观察 Live Telemetry / Glucose Trend / Intervention Timeline
4. 汉堡菜单切到 **Home** 页：
   - **Scenario B（硬预警）**：红色弹窗立即出现
   - **Scenario A（软预警）**：等 ~30s Agent 处理，首页文案变化
5. 回 Demo Console 点 **Reset Today** 清除数据

---

## 关键配置文件

| 文件 | 作用 |
|---|---|
| `.env` | 环境变量：数据库、Redis、API Key、Twilio 等 |
| `config.py`（根目录） | Python 后端共享配置，用 pydantic-settings 读取 `.env` |
| `chatbot/config/settings.py` | Chatbot 独立配置（SEA-LION、MERaLiON 模型参数） |
| `frontend/next.config.mjs` | Next.js 配置 |

---

## 常见问题

| 问题 | 解决 |
|---|---|
| `Unable to acquire lock` (next dev) | `lsof -ti :3000 \| xargs kill -9` 杀掉残留进程 |
| `ModuleNotFoundError: config` | 确认根目录有 `config.py` |
| `ModuleNotFoundError: xxx` | 确认已 `source .venv/bin/activate` |
| Gateway 返回 500 | 检查 `.env` 的数据库配置，确认云端 PG 可达 |
| 软预警没反应 | 确认 Redis + Alert Agent (Celery) 都已启动 |
| `Connection refused :8000` | Gateway 没启动 |
| `Connection refused :8080` | Chatbot 没启动 |
| 前端页面白屏 | 打开浏览器 DevTools Console 看报错 |

---

## 关闭服务

- 各终端 `Ctrl+C` 停止
- Redis 后台模式：`brew services stop redis`
- 退出虚拟环境：`deactivate`
