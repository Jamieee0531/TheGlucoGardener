# Marcus Demo 前端可视化演示 — 方案文档

> 基于 `seed_user_002_design.md` 的故事线，结合已有 Gateway API 和前端框架，  
> 新建一套 **Demo 演示控制台 + Home 页动态预警展示**。

---

## 一、现状分析

### 已有的后端能力
| 模块 | 状态 | 说明 |
|---|---|---|
| Gateway `/telemetry/cgm` | ✅ | 接收血糖 → persist + hard/soft trigger |
| Gateway `/telemetry/hr` | ✅ | 接收心率 → persist + hard trigger |
| Gateway `/test/reset-today` | ✅ | 清除当天数据 |
| Alert Agent (Celery + LangGraph) | ✅ | investigator → reflector → communicator |
| InterventionLog 表 | ✅ | 记录所有触发和推送 |
| Scenario JSON 文件 | ✅ | 7 个通用 + 需新增 3 个 Marcus 专用 |

### 已有的前端能力
| 页面 | 状态 | 说明 |
|---|---|---|
| `page.js` (Home) | ✅ | 静态问候 + 统计 + 血糖图 |
| `soft-alert/page.js` | 🟡 纯静态参考 | 硬编码文案，仅做 UI 参考 |
| `hard-alert/page.js` | 🟡 纯静态参考 | 弹窗硬编码，仅做 UI 参考 |
| `SugarChart.js` | 🟡 假数据 | 静态 SVG 折线，无真实血糖数据 |
| `lib/api.js` | ✅ | 仅 chatbot API (port 8080)，无 Gateway 集成 |

### 两个后端服务
| 服务 | 端口 | 职责 |
|---|---|---|
| Chatbot (FastAPI) | 8080 | `/chat/message`, `/chat/stream`, Garden API |
| Gateway (FastAPI) | 8000 | `/telemetry/*`, `/test/*`, `/crud/*`, Alert 触发 |

### 缺失的前端部分
1. **Demo 控制台页面** — 汉堡菜单入口，加载 JSON 剧本并发送 API
2. **Home 页预警展示** — 软预警文案替换 + 硬预警弹窗
3. **Gateway API 客户端** — 前端调用 Gateway (port 8000) 的封装
4. **跨页面通信机制** — Demo 页触发 → Home 页展示
5. **Marcus 专用 Scenario JSON** — 3 个剧本文件

---

## 二、核心交互流程

### 2.1 总体流程

```
用户在 Demo 控制台点击 Play
        ↓
ScenarioPlayer 逐步调用 Gateway API
        ↓
Gateway 处理触发逻辑
        ↓
用户手动切换到 Home 页
        ↓
Home 页展示预警效果
```

### 2.2 软预警流程 (Scenario A)

```
Demo 页 → POST /telemetry/hr + /telemetry/cgm
       → Gateway 判定 soft trigger → Celery → Agent 推理 (~30s)
       → Agent 写 InterventionLog (message_sent = Communicator 文案)

用户切到 Home 页
       → Home 页轮询 GET /crud/interventions (每 3s)
       → 发现 soft intervention 记录
       → Section 1 变化:
           "How are you feeling?" → "Heads up!"
           新增 Communicator 的 message_sent 文案
           隐藏 healthy_life.jpg
           显示 "已读" 按钮
       → 用户点击 "已读" → 恢复默认文案 + 显示 healthy_life.jpg
```

### 2.3 硬预警流程 (Scenario B)

```
Demo 页 → POST /telemetry/cgm (glucose=3.8)
       → Gateway 返回 { status: "received", hard_fired: true, trigger_type: "hard_low_glucose" }
       → Demo 页立即写 localStorage: hard_alert = { trigger_type, glucose, timestamp }

用户切到 Home 页
       → useEffect 检查 localStorage 中的 hard_alert
       → 立即弹出红色全屏弹窗 (参考 hard-alert/page.js 的 modal 样式)
       → 用户点右上角 × → 清除 localStorage → 关闭弹窗
```

### 2.4 跨页面通信方案

| 预警类型 | 通信机制 | 延迟 | 说明 |
|---|---|---|---|
| 硬预警 | localStorage 直写 | ~0s (即时) | Gateway 响应 → Demo 页写入 → Home 页读取 |
| 软预警 | 轮询后端 InterventionLog | ~3s (轮询间隔) | Agent 异步处理 ~30s，轮询延迟可忽略 |
| 兜底 | Home 页同时轮询 InterventionLog | ~3s | 硬预警也会写 InterventionLog，轮询可兜底 |

---

## 三、新建 & 修改文件清单

### 新建文件
```
frontend/src/
├── app/demo/
│   └── page.js                    # [新建] Demo 演示控制台 (汉堡菜单入口)
├── components/
│   ├── ScenarioPlayer.jsx         # [新建] 剧本播放器组件
│   ├── TelemetryPanel.jsx         # [新建] 实时遥测数据面板 (Demo 页内)
│   ├── InterventionTimeline.jsx   # [新建] Agent 干预事件时间线 (Demo 页内)
│   └── LiveSugarChart.jsx         # [新建] 实时血糖折线图 (Demo 页内)
├── lib/
│   └── gatewayApi.js              # [新建] Gateway API 客户端 (port 8000)

frontend/public/scenarios/
├── marcus_soft_pre_exercise.json  # [新建] 剧本 A
├── marcus_hard_low_glucose.json   # [新建] 剧本 B
└── marcus_no_trigger.json         # [新建] 剧本 C
```

### 修改文件
```
frontend/src/app/page.js           # [改] Home 页: 软预警文案替换 + 硬预警弹窗
gateway/routers/telemetry.py       # [改] /telemetry/cgm 响应增加 hard_fired 字段
gateway/routers/crud.py            # [改] 新增 GET /crud/interventions 端点
```

### 保留不动
```
frontend/src/app/soft-alert/page.js   # 保留作为 UI 参考
frontend/src/app/hard-alert/page.js   # 保留作为 UI 参考
```

---

## 四、各组件详细设计

### 4.1 `lib/gatewayApi.js` — Gateway API 客户端

```js
const GATEWAY_URL = "http://localhost:8000";

// Demo 控制台调用
postCGM(user_id, glucose, recorded_at?)      → POST /telemetry/cgm
postHR(user_id, heart_rate, gps_lat, gps_lng, recorded_at?) → POST /telemetry/hr
resetToday(user_id)                           → POST /test/reset-today

// Home 页轮询调用
fetchInterventions(user_id, today_only=true)  → GET /crud/interventions
```

---

### 4.2 `app/page.js` (Home 页) — 预警展示改造

**核心改动: Section 1 条件渲染**

```
默认状态:
┌─────────────────────────┐
│ Good morning Marcus!    │
│ How are you feeling?    │
│ [Chat with AI]          │
│ 🖼 healthy_life.jpg     │
└─────────────────────────┘

软预警状态 (softAlert 存在时):
┌─────────────────────────┐
│ Good morning Marcus!    │
│ ⚠ Heads up!             │
│ {message_sent 文案}      │
│ [Chat with AI]          │
│ [已读 ✓]                │
│ (healthy_life.jpg 隐藏)  │
└─────────────────────────┘

硬预警状态 (hardAlert 存在时):
┌─────────────────────────┐
│ (Home 正常内容)          │
│                         │
│  ┌── 红色弹窗 ────────┐ │
│  │  ×                  │ │
│  │  🍬                 │ │
│  │  Hypoglycemia Alert │ │
│  │  {硬预警文案}        │ │
│  └─────────────────────┘ │
└─────────────────────────┘
```

**状态管理逻辑:**
```
useEffect:
  1. 检查 localStorage "hard_alert" → 有则 setHardAlert(data)
  2. 启动 setInterval 每 3s 调用 fetchInterventions(user_id)
     → 有 soft intervention 且 user_ack=false → setSoftAlert(data)

点击 "已读":
  → setSoftAlert(null)
  → 可选: 调用后端 PATCH intervention.user_ack = true

点击 × 关闭硬预警弹窗:
  → setHardAlert(null)
  → localStorage.removeItem("hard_alert")
```

---

### 4.3 `ScenarioPlayer.jsx` — 剧本播放器

**功能:**
1. 下拉菜单选择 scenario JSON（Marcus 的 3 个剧本）
2. 展示剧本描述和预期结果
3. 每个 step 显示为卡片，包含 endpoint / body / note
4. "▶ Play All" 按钮：按 `offset_minutes` 延迟依次发送请求
5. 也可单步点击发送（方便讲解时逐步操作）
6. "Reset Today" 按钮：调用 `/test/reset-today` + 清除 localStorage
7. 每步发送后显示状态和响应
8. **硬预警处理**: 如果响应包含 `hard_fired: true`，立即写 localStorage

**Scenario JSON 加载方式:**
将 3 个 JSON 放到 `frontend/public/scenarios/`，前端 `fetch("/scenarios/xxx.json")` 加载。

**演示时序处理:**
- `offset_minutes` 在 JSON 中定义为现实时间偏移
- Demo 模式下映射为秒级延迟: `DEMO_SPEED = 1000` (1 min → 1 sec)
- 即 `offset_minutes: 3` → 等待 3 秒后发送

---

### 4.4 `TelemetryPanel.jsx` — 实时遥测面板

**功能:** 在 Demo 控制台内展示 Marcus 当前生理指标，随每步更新。

```
┌─────────────────────────────────────┐
│  Glucose: 4.9 mmol/L        ⚠ LOW  │
│  HR: 138 bpm                @ GYM  │
│  GPS: ActiveSG Gym                  │
│  Last update: 14:03                 │
└─────────────────────────────────────┘
```

**状态着色:**
| 指标 | 正常 (绿) | 注意 (黄) | 危险 (红) |
|---|---|---|---|
| Glucose | > 5.6 | 3.9 - 5.6 | < 3.9 |
| HR | < 120 | 120-145 | > 145 |

**数据来源:** 直接从 ScenarioPlayer 的 step body 提取，不额外调 API。

---

### 4.5 `LiveSugarChart.jsx` — 实时血糖折线图

**功能:**
- 展示 scenario 过程中收到的血糖数据点
- 标注安全范围带（3.9-10.0 浅绿背景）
- 标注危险阈值线（3.9 红色虚线）
- 当前值用大圆点高亮

**技术:** 纯 SVG，沿用现有 `SugarChart.js` 风格，无新依赖。

---

### 4.6 `InterventionTimeline.jsx` — Agent 干预时间线

**功能:** 在 Demo 控制台内展示当前 scenario 触发的 intervention 事件。

```
14:00  SOFT_PRE_EXERCISE_LOW_BUFFER
       Agent: avg_drop=0.86, projected=4.04
       Message: "Hey Marcus! Your glucose is 4.9..."
       Status: Sent

14:07  HARD_LOW_GLUCOSE
       Glucose: 3.8 < 3.9 threshold
       Status: Emergency fired
```

**数据来源:** 轮询 `GET /crud/interventions`，每 3s 一次。

---

### 4.7 `app/demo/page.js` — Demo 控制台

**入口:** 汉堡菜单新增 "Demo Console" 选项。

**布局:**
```
┌──────────────────────────────────────────────────────────┐
│  Demo Console — Marcus's Story            [user_002]     │
├────────────────────┬─────────────────────────────────────┤
│                    │                                     │
│  ScenarioPlayer    │  TelemetryPanel                     │
│  ┌──────────────┐  │  ┌─────────────────────────────┐    │
│  │ 选择剧本 ▼   │  │  │ Glucose / HR / GPS 面板     │    │
│  │              │  │  └─────────────────────────────┘    │
│  │ Step 1: ...  │  │                                     │
│  │ Step 2: ...  │  │  LiveSugarChart                     │
│  │              │  │  ┌─────────────────────────────┐    │
│  │ [▶ Play All] │  │  │ 血糖折线图                   │    │
│  │ [Reset]      │  │  └─────────────────────────────┘    │
│  └──────────────┘  │                                     │
│                    │  InterventionTimeline                │
│  提示:             │  ┌─────────────────────────────┐    │
│  Play 后切换到     │  │ Agent 事件列表               │    │
│  Home 页查看效果   │  └─────────────────────────────┘    │
│                    │                                     │
├────────────────────┴─────────────────────────────────────┤
│  ⓘ 软预警需等待 Agent 处理 (~30s), 硬预警即时生效        │
└──────────────────────────────────────────────────────────┘
```

---

## 五、后端改动

### 5.1 `gateway/routers/telemetry.py` — CGM 响应增加触发信息

**现状:** `POST /telemetry/cgm` 返回 `{"status": "received"}`

**改为:**
```json
{
  "status": "received",
  "hard_fired": true,
  "trigger_type": "hard_low_glucose"
}
```

改动点: `receive_cgm()` 函数返回值中加入 `hard_fired` 和 `trigger_type`。
已有变量 `hard_fired` (evaluate_hard_triggers 的返回值), 只需透传。

### 5.2 `gateway/routers/crud.py` — 新增 Intervention 查询端点

```
GET /crud/interventions?user_id=user_002&today_only=true

Response:
[
  {
    "id": 1,
    "trigger_type": "soft_pre_exercise_low_buffer",
    "display_label": "Pre-Exercise Low Buffer",
    "agent_decision": "avg_drop=0.86, projected=4.04",
    "message_sent": "Hey Marcus! Your glucose is 4.9...",
    "triggered_at": "2026-04-04T14:00:00",
    "user_ack": false
  }
]
```

查 InterventionLog 表，过滤 user_id + 今日日期，按 triggered_at 降序。

---

## 六、3 个 Marcus Scenario JSON

### `marcus_soft_pre_exercise.json`
```json
{
  "scenario_id": "marcus_soft_pre_exercise",
  "title": "Scenario A: Pre-Exercise Soft Alert",
  "description": "Marcus arrives at gym, glucose 4.9. Agent predicts post-exercise drop to 4.04.",
  "user_id": "user_002",
  "steps": [
    {
      "offset_minutes": 0,
      "endpoint": "POST /telemetry/hr",
      "body": {"heart_rate": 78, "gps_lat": 1.3200, "gps_lng": 103.8400},
      "note": "Marcus arrives at ActiveSG Gym, resting HR"
    },
    {
      "offset_minutes": 0,
      "endpoint": "POST /telemetry/cgm",
      "body": {"glucose": 4.9},
      "note": "4.9 in [4.0, 5.6] + Saturday workout -> SOFT_PRE_EXERCISE"
    }
  ],
  "expected_outcome": "SOFT_TRIGGER -> Investigator -> Reflector (avg_drop=0.86) -> Communicator push"
}
```

### `marcus_hard_low_glucose.json`
```json
{
  "scenario_id": "marcus_hard_low_glucose",
  "title": "Scenario B: Exercise Hard Low Glucose",
  "description": "Marcus ignored soft alert. 7 min into workout, glucose crashes to 3.8.",
  "user_id": "user_002",
  "steps": [
    {
      "offset_minutes": 0,
      "endpoint": "POST /telemetry/hr",
      "body": {"heart_rate": 138, "gps_lat": 1.3200, "gps_lng": 103.8400},
      "note": "Marcus exercising, HR elevated"
    },
    {
      "offset_minutes": 0,
      "endpoint": "POST /telemetry/cgm",
      "body": {"glucose": 4.5},
      "note": "Glucose dropping, still safe"
    },
    {
      "offset_minutes": 3,
      "endpoint": "POST /telemetry/hr",
      "body": {"heart_rate": 155, "gps_lat": 1.3200, "gps_lng": 103.8400},
      "note": "High exertion, mid-rep"
    },
    {
      "offset_minutes": 3,
      "endpoint": "POST /telemetry/cgm",
      "body": {"glucose": 3.8},
      "note": "CRITICAL: < 3.9 -> HARD TRIGGER -> Emergency"
    }
  ],
  "expected_outcome": "HARD_TRIGGER -> EmergencyService -> App push + red modal"
}
```

### `marcus_no_trigger.json`
```json
{
  "scenario_id": "marcus_no_trigger",
  "title": "Scenario C: Normal Readings (Control)",
  "description": "Normal Saturday readings. System correctly stays silent.",
  "user_id": "user_002",
  "steps": [
    {
      "offset_minutes": 0,
      "endpoint": "POST /telemetry/hr",
      "body": {"heart_rate": 72, "gps_lat": 1.3521, "gps_lng": 103.8198},
      "note": "Marcus at home, resting"
    },
    {
      "offset_minutes": 0,
      "endpoint": "POST /telemetry/cgm",
      "body": {"glucose": 6.5},
      "note": "6.5 — safe range, no trigger"
    }
  ],
  "expected_outcome": "No trigger. No notifications. System quiet = system normal."
}
```

---

## 七、演示流程（前端视角）

### Step 1: 打开 Demo 控制台
- 汉堡菜单 → Demo Console
- 页面自动锁定 `user_002` (Marcus)

### Step 2: Scenario A — 运动前软触发
1. 下拉选择 `marcus_soft_pre_exercise`
2. 点击 Play All → 2 个请求发出 → 步骤显示 ✅
3. 右侧面板: Glucose 4.9 (黄), HR 78 (绿), GPS @ Gym
4. 汉堡菜单切到 Home 页
5. Home 页轮询中，约 30s 后 Section 1 变化:
   - "How are you feeling?" → "Heads up!"
   - 显示 Communicator 文案: "Hey Marcus! Your glucose is 4.9..."
   - healthy_life.jpg 隐藏
6. 点击 "已读" → 恢复默认

### Step 3: Reset
1. 汉堡菜单回到 Demo Console
2. 点击 Reset Today → 清除数据 + localStorage

### Step 4: Scenario B — 运动中硬触发
1. 选择 `marcus_hard_low_glucose`
2. 点击 Play All
3. Step 1-2 立即发出 (HR 138, Glucose 4.5)
4. 等 3s → Step 3-4 发出 (HR 155, Glucose 3.8)
5. Gateway 返回 `hard_fired: true` → localStorage 写入
6. 切到 Home 页 → 立即弹出红色弹窗
7. 点 × 关闭

### Step 5: (可选) Scenario C — 对照组
1. Reset → 选择 `marcus_no_trigger` → Play
2. 切到 Home → 一切正常，无预警

---

## 八、技术决策

| 决策点 | 方案 | 理由 |
|---|---|---|
| 硬预警通信 | localStorage 直写 | Gateway 响应同步，即时生效 |
| 软预警通信 | 轮询 InterventionLog (3s) | Agent 异步 ~30s，轮询延迟可忽略 |
| 图表库 | 纯 SVG | 已有 SugarChart 先例，零新依赖 |
| Scenario 加载 | `public/scenarios/` + fetch | 简单，可热更新 JSON |
| Demo 入口 | 汉堡菜单 | 不破坏现有页面结构 |
| 时间加速 | `offset_minutes` → 秒 | `DEMO_SPEED = 1000` (1 min = 1 sec) |

---

## 九、依赖与风险

### 无需新增 npm 依赖
所有组件用 React + Tailwind + 纯 SVG。

### 风险项
| 风险 | 影响 | 缓解 |
|---|---|---|
| Alert Agent 未运行 | 软预警无 intervention 返回 | Home 页显示 "Waiting..." + 轮询超时提示 |
| PostgreSQL 未启动 | Gateway 写入失败 | Demo 页显示连接状态 |
| Redis/Celery 未启动 | 软预警任务无法入队 | 仅硬预警可正常演示 |
| seed_user_002 未执行 | 历史数据缺失 | Demo 页提示 "Run seed first" |

---

## 十、工作量估算

| 文件 | 类型 | 复杂度 |
|---|---|---|
| `lib/gatewayApi.js` | 工具函数 | 低 |
| `components/ScenarioPlayer.jsx` | 组件 | 中 |
| `components/TelemetryPanel.jsx` | 组件 | 低 |
| `components/LiveSugarChart.jsx` | 组件 | 中 |
| `components/InterventionTimeline.jsx` | 组件 | 低 |
| `app/demo/page.js` | 页面 | 中 |
| `app/page.js` 改造 | 页面修改 | 中 |
| 3 个 Marcus Scenario JSON | 数据 | 低 |
| `telemetry.py` 响应改造 | 后端 | 低 |
| `crud.py` 新增 GET 端点 | 后端 | 低 |
| **总计** | **~10 个文件** | |

---

## 十一、建议实施顺序

1. **Phase 0**: 创建 3 个 Marcus Scenario JSON → `frontend/public/scenarios/`
2. **Phase 1**: 后端改动 — `telemetry.py` 响应加 hard_fired + `crud.py` 加 GET interventions
3. **Phase 2**: `gatewayApi.js` + `ScenarioPlayer.jsx` + `app/demo/page.js` — 能发请求
4. **Phase 3**: `app/page.js` 改造 — 软预警文案替换 + 硬预警弹窗 + 轮询/localStorage
5. **Phase 4**: `TelemetryPanel.jsx` + `LiveSugarChart.jsx` + `InterventionTimeline.jsx` — Demo 页可视化
6. **Phase 5**: 汉堡菜单加入 Demo Console 入口 + 整体联调
