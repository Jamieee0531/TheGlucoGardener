# TheGlucoGardener 本地运行指南

## 架构总览

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Frontend    │────▶│  Chatbot API     │────▶│  PostgreSQL      │
│  Next.js     │     │  FastAPI :8080   │     │  (云端，见 .env) │
│  :3000       │     └──────┬───────────┘     └──────────────────┘
│              │            │ (可选)                   ▲
│              │            ▼                          │
│              │     ┌──────────────────┐              │
│              │     │  MCP Server      │              │
│              │     │  FastAPI :8002   │              │
│              │     │  PubMed/OpenFDA/ │              │
│              │     │  本地 RAG        │              │
│              │     └──────────────────┘              │
│              │                                       │
│              │     ┌──────────────────┐              │
│              │────▶│  Gateway API     │──────────────┘
│              │     │  FastAPI :8000   │
│              │     └───────┬──────────┘
│              │             │ dispatch task via Celery
│              │             ▼
│              │     ┌──────────────────┐     ┌──────────────────┐
│              │     │  Redis           │────▶│  Alert Agent     │
│              │     │  :6379           │     │  Celery Worker   │
│              │     └──────────────────┘     └──────────────────┘
│              │
│              │     ┌──────────────────┐
│              │────▶│  Task Agent      │
│              │     │  FastAPI :8001   │
└─────────────┘     └──────────────────┘

                    ┌──────────────────┐
                    │  Pipeline        │  ← 独立运行，不接受 HTTP 请求
                    │  Scheduler /     │
                    │  Backfill        │
                    └──────────────────┘
```

| 服务 | 端口 | 职责 |
|---|---|---|
| **Frontend** (Next.js) | 3000 | 用户界面、Demo Console |
| **Gateway API** (FastAPI) | 8000 | 遥测数据接收、触发判定、干预记录查询 |
| **Task Agent** (FastAPI) | 8001 | 动态任务生成、任务卡片 API |
| **MCP Server** (FastAPI) | 8002 | 医学知识检索（PubMed / OpenFDA / 本地 RAG） |
| **Chatbot API** (FastAPI) | 8080 | 聊天、花园、用户资料、血糖查询、餐食记录、图片分析 |
| **Redis** | 6379 | Celery 消息队列（Alert Agent 的任务通道） |
| **Alert Agent** (Celery Worker) | — | LangGraph 异步推理：Investigator → Reflector → Communicator |
| **Pipeline** | — | 数据聚合（夜间定时 / 手动 backfill），不监听端口 |
| **PostgreSQL** | 5432 | 数据库（已云端部署，连接信息在 `.env`） |

---

## 前置条件

- **Node.js** >= 18
- **Python** >= 3.11
- **Redis**（macOS: `brew install redis`）
- 项目根目录有 `.env` 文件（数据库、API Key 等，所有后端服务共享此文件）
- 项目根目录有 `config.py`（Python 后端共享配置，读取 `.env`）

### `.env` 关键变量

```bash
# 数据库
PG_HOST=         # 云端 RDS 地址
PG_PORT=5432
PG_USER=
PG_PASSWORD=
PG_DB=

# Redis
REDIS_URL=redis://127.0.0.1:6379/0

# LLM（至少配一个）
GEMINI_API_KEY=
LLM_MODEL=gemini-2.5-flash        # Alert Agent 使用的模型
SEALION_API_KEY=                   # Chatbot SEA-LION 模型
MERALION_API_KEY=                  # Chatbot MERaLiON 语音模型

# 图片分析
VLM_PROVIDER=gemini                # Vision Language Model 提供商

# 通知（可选）
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=
FCM_SERVER_KEY=

# 其他
SECRET_KEY=
LOG_LEVEL=DEBUG
DEMO_MODE=true
EMOTION_STALENESS_HOURS=2
PIPELINE_SCHEDULE_HOUR=2           # Pipeline 每日执行时间
PIPELINE_SCHEDULE_MINUTE=0
```

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
python -m pip install -r requirements.txt
```

> 也可以用 `make install` 一键完成。

### 3. 数据库初始化

数据库 schema 定义在 `alert_db/init.sql`。如果是全新数据库，需要手动执行：

```bash
# 使用 psql 连接云端数据库并执行建表
psql "postgresql://$PG_USER:$PG_PASSWORD@$PG_HOST:$PG_PORT/$PG_DB" -f alert_db/init.sql
```

> **注意：** Task Agent 的表会在服务启动时通过 SQLAlchemy 自动创建，不需要手动操作。

### 4. Demo 数据注入

```bash
source .venv/bin/activate

# 注入 Marcus (user_002) 的完整 Demo 测试数据
python demo/seed_user_002.py
```

> seed 脚本会先清除 user_002 的旧数据再重新写入，可安全重复执行。
> **注意：** 每次 Demo 当天需要重跑一次 seed，确保"今天"的食物记录日期正确。

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

### 终端 3 — Task Agent (port 8001)

```bash
source .venv/bin/activate
uvicorn task_agent.main:app --host 0.0.0.0 --port 8001 --reload
```

验证：`http://localhost:8001/health` → `{"status":"ok","service":"task_agent"}`

### 终端 4 — Chatbot API (port 8080)

```bash
source .venv/bin/activate
uvicorn chatbot.api.main:api --host 0.0.0.0 --port 8080 --reload
```

> **注意：** Chatbot 的 FastAPI 实例变量名是 `api` 不是 `app`。

验证：`http://localhost:8080/docs` → 看到 Swagger UI

### 终端 5 — Alert Agent (Celery Worker)

软预警（Scenario A）必须启动此服务。

```bash
source .venv/bin/activate
celery -A alert_agent.main worker --loglevel=info
```

### 终端 6 — Frontend (port 3000)

```bash
cd frontend
npm run dev
```

验证：`http://localhost:3000` → 看到登录页面

### 终端 7（可选）— MCP Server (port 8002)

仅 Chatbot RAG 医学知识检索需要。

```bash
source .venv/bin/activate
python -m chatbot.mcp.server
```

验证：`http://localhost:8002/docs` → 看到 Swagger UI

### 终端 8（可选）— Pipeline Scheduler

数据聚合服务，使用 APScheduler 每日定时运行血糖 profile 聚合。生产环境需要，本地 Demo 可以跳过。

```bash
source .venv/bin/activate
python pipeline/run.py
```

手动 backfill 某用户的历史数据：

```bash
python pipeline/run.py --backfill --user_id user_002
```

---

## 按需启动（不用每次全开）

| 测试目的 | 需要启动的服务 |
|---|---|
| 只看前端 UI / 页面布局 | Frontend |
| 聊天 / 花园 / 用户资料 | Frontend + Chatbot API |
| 任务卡片 / 动态任务 | Frontend + Task Agent |
| Demo Console + 硬预警 | Frontend + Gateway API |
| Demo Console + 软预警（完整 Agent Pipeline） | Frontend + Gateway API + Redis + Alert Agent |
| Chatbot 医学知识问答 | Frontend + Chatbot API + MCP Server |
| 完整联调 | 全部服务 |

---

## Demo Console 测试流程

1. `http://localhost:3000` → 登录 → 汉堡菜单 → **Demo Console**
2. 选 Scenario A → 点 **Play All**
3. 观察 Agent Pipeline 区域：Investigator Node（硬编码展示）→ 等待 Reflector / Communicator（约 30s）
4. 汉堡菜单切到 **Home** 页 → 黄色 Soft Alert 弹窗出现
5. 回 Demo Console 点 **Reset Today** 清除数据

### Demo Scenarios 说明

Demo 场景数据定义在 `demo/scenarios/` 目录下：

| 文件 | 类型 | 说明 |
|---|---|---|
| `soft_trigger_pre_exercise.json` | 软预警 | 运动前低血糖风险（Scenario A 主场景） |
| `soft_trigger_slope.json` | 软预警 | 血糖斜率持续下降 |
| `soft_trigger_reflector_reject.json` | 软预警 | Reflector 拒绝干预的示例 |
| `hard_trigger_low_glucose.json` | 硬预警 | 血糖低于紧急阈值 |
| `hard_trigger_high_hr.json` | 硬预警 | 心率异常偏高 |
| `hard_trigger_data_gap.json` | 硬预警 | 传感器数据中断 |
| `no_trigger.json` | 无触发 | 正常数据不触发预警 |

### Scenario A（软预警）剧情

- 13:31 Marcus 到达 ActiveSG Gym，glucose = 4.9 mmol/L
- 14:00 即将开始 HIIT（45 分钟）
- Agent 推理：历史 3 次 HIIT 平均 glucose drop 1.03 → 预测降到 3.87（低于 3.9 危险线）
- 加上全天仅摄入 670 kcal（早餐 06:30 Kaya Toast + Kopi，午餐 11:30 Chicken Sandwich）
- 触发 Soft Alert 提醒用户补充碳水

---

## Makefile 快捷命令

```bash
make install          # 创建虚拟环境 + 安装依赖
make test             # 运行所有测试
make coverage         # 运行测试 + 覆盖率报告
make lint             # 运行 ruff 代码检查
make run IMG=<路径>   # Vision Agent CLI（mock 模式）
make run-gemini IMG=<路径>  # Vision Agent CLI（Gemini 模式）
make clean            # 清理虚拟环境和缓存
```

---

## 关键配置文件

| 文件 | 作用 |
|---|---|
| `.env` | 环境变量：数据库、Redis、API Key、Twilio 等（所有后端服务共享） |
| `config.py`（根目录） | Gateway / Alert Agent / Pipeline 共享配置，用 pydantic-settings 读取 `.env` |
| `task_agent/config.py` | Task Agent 配置，用 pydantic-settings 读取根目录 `.env` |
| `chatbot/config/settings.py` | Chatbot 独立配置（SEA-LION、MERaLiON 模型参数），用 dotenv 读取根目录 `.env` |
| `alert_db/init.sql` | 数据库 schema 定义（PostgreSQL DDL） |
| `alert_db/models.py` | SQLAlchemy ORM 模型定义 |
| `frontend/next.config.mjs` | Next.js 配置 |
| `Procfile` | 云端部署入口（仅定义 Chatbot API web 进程） |

---

## 常见问题

| 问题 | 解决 |
|---|---|
| `Unable to acquire lock` (next dev) | `lsof -ti :3000 \| xargs kill -9` 杀掉残留进程 |
| `ModuleNotFoundError: config` | 确认根目录有 `config.py`，且在项目根目录下执行命令 |
| `ModuleNotFoundError: xxx` | 确认已 `source .venv/bin/activate` |
| Gateway 返回 500 | 检查 `.env` 的数据库配置，确认云端 PG 可达 |
| 软预警没反应 | 确认 Redis + Alert Agent (Celery) 都已启动 |
| 任务卡片加载失败 | 确认 Task Agent (port 8001) 已启动 |
| Chatbot 图片分析失败 | 确认 `.env` 中 `VLM_PROVIDER` 和对应 API Key 已配置 |
| `Connection refused :8000` | Gateway 没启动 |
| `Connection refused :8001` | Task Agent 没启动 |
| `Connection refused :8080` | Chatbot 没启动 |
| 前端页面白屏 | 打开浏览器 DevTools Console 看报错 |
| seed 脚本 `UniqueViolationError` | 正常，脚本已包含清理逻辑，如仍报错检查是否使用最新版脚本 |
| reasoning_summary 内容过时 | 重跑 `python demo/seed_user_002.py`，重启 Celery worker |
| MCP Server 连接失败 | 确认 port 8002 没被占用，Chatbot 需先启动 |

---

## 关闭服务

- 各终端 `Ctrl+C` 停止
- Redis 后台模式：`brew services stop redis`
- 退出虚拟环境：`deactivate`
