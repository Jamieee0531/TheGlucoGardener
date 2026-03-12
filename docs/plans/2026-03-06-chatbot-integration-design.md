# Design: Chatbot Integration + Enhancement

> Date: 2026-03-06 | Author: Jamie | Status: Approved

## Context

- Vision Agent 已完成（171 tests, 99% coverage）
- Bailey 的 Health-Companion chatbot 已 clone 到本地
- 目标：3.19 前完成 prototype，预录 demo 视频
- 不做微调，不做数据持久化（mock 先撑），不做 MERaLiON 语音

## Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Scope | Vision 集成 + chatbot 完善 | 数据持久化最后做 |
| Integration | 直接 import（非 API） | prototype 阶段能简则简 |
| Demo | 预录视频 | 容错压力小 |
| Repo | 本地 Health-Companion 直接改 | 无 push 权限，本地开发 |
| Division | Jamie 主导，后续与 Bailey 对齐 | |
| Downstream | 设计保留，3.19 只 log 不对接 | |

---

## Section 1: Architecture — Vision Integration

### Current Flow (Bailey)

```
用户文字 → triage（意图+情绪） → policy（策略规则） → 5个Agent之一 → 回复
```

### New Flow

```
用户输入（文字 / 图片）
    |
input_node（new）— 判断输入类型
    |-- 纯文字 → 直接往下
    |-- 有图片+有文字 → Vision Agent 识别，文字照常走
    |-- 只有图片 → Vision Agent 识别，根据 scene_type 自动生成一句话
    |              food → "我拍了一张食物照片"
    |              medication → "我拍了一张药物照片"
    |
    v
vision_result 存入 state（列表，支持多图）
    |
    v
triage → policy → Agent → 回复
                    |
            Expert Agent 读取 vision_result
            根据置信度决定跳过/确认/追问
```

### Key Changes

1. LangGraph 图在 triage 前加 `input_node`
2. state 新增 `vision_result` 字段（list）
3. Expert Agent 追问逻辑改为 state 驱动
4. Bailey 的 triage → policy → agent 主线不动

### Expert Agent State Machine — Confidence-Driven

每个信息字段有三种状态：

| 状态 | 条件 | Expert 行为 |
|------|------|------------|
| empty | 无值，或 confidence < 0.5 | 追问 |
| uncertain | 有值，confidence 0.5~0.8 | 确认："看起来是 XX，对吗？" |
| confirmed | 有值，confidence >= 0.8，或用户手动回答 | 跳过 |

Expert 每轮检查 state 中的字段（glucose, diet, medication），全部 confirmed 后给综合建议。

---

## Section 2: Chatbot Enhancement — Priorities

### P0 (demo must-have)

1. **Triage 意图分类优化** — 关键词预分类 + LLM 兜底（不做微调）
2. **Expert Agent 追问链重构** — 固定顺序改为 state 驱动
3. **Companion Agent 危机检测** — 自伤关键词检测 + 危机热线输出

### P1 (demo nice-to-have)

4. **情绪感知影响回复风格** — Agent prompt 根据情绪调整语气
5. **限流降级** — SEA-LION 超限时自动切备用模型

### P2 (design only, 3.19 not implemented)

6. **MERaLiON 语音** — API 审批中，先跳过
7. **下游触发器** — log 输出 alert_trigger / task_trigger，不真正对接
8. **数据持久化** — 保持 mock，最后做

---

## Section 3: Demo Golden Path

5 步预录视频，约 2-3 分钟，覆盖所有核心功能：

### Step 1: Chitchat

```
User: "你好"
Triage: chitchat
Agent: Chitchat
Response: "你好呀！我是你的健康助手，有什么可以帮你的？"
```

### Step 2: Food Photo → Expert (skip diet question)

```
User: [sends chicken rice photo, no text]
input_node: image detected, no text → Vision Agent
Vision: {scene_type: "food", name: "海南鸡饭", calories: 600, gi: "高", confidence: 0.85}
Auto-text: "我拍了一张食物照片"
Triage: medical → Expert Agent
Expert state: diet = confirmed (0.85)
Response: "这是海南鸡饭，约 600 大卡，GI 偏高。你目前血糖情况怎么样？"
```

### Step 3: Text → Expert (glucose collected)

```
User: "最近空腹血糖 7.2"
Triage: medical → Expert Agent
Expert state: glucose = confirmed
Response: "了解。你目前在吃什么药吗？"
```

### Step 4: Medication Photo → Expert (all confirmed → advice)

```
User: [sends Metformin photo]
input_node → Vision Agent
Vision: {scene_type: "medication", name: "Metformin", dosage: "500mg", confidence: 0.9}
Expert state: medication = confirmed → ALL confirmed
Response: "你在服用二甲双胍 500mg，空腹血糖 7.2 偏高。海南鸡饭 GI 较高，建议..."
Log output: alert_trigger (glucose elevated)
```

### Step 5: Emotion Switch → Companion

```
User: "唉，我最近压力好大，管不住嘴"
Triage: emotional
Policy: emotion-first strategy
Agent: Companion
Response: "我理解你的感受，控制饮食确实不容易..."
```

### Coverage

- Chitchat, Food recognition, Medication recognition
- Multi-turn follow-up with state-driven skipping
- Confidence-based confirm/skip/ask
- Emotion detection + agent switch
- Downstream trigger (log)

---

## Section 4: Multi-Intent & Task Trigger Design（2026-03-07 补充）

### 系统整体架构（下游关系）

```
用户
  → Chatbot（Health-Companion）— 本 repo
       → 输出 task_trigger → Task Agent（Chayi）
       → 输出 alert_trigger → Alert Agent（Julia）
```

Chatbot 只负责检测"事件发生"并输出信号，具体任务逻辑由下游模块决定。

### 多意图处理机制（Bailey 设计）

- `triage` 返回 `all_intents: list`，可包含多个意图
- **路由只选主意图（`intent`）走一个 Agent**
- 其他意图通过 Agent 内部 prompt 融合（不路由到多个 Agent）
- 例如：`["medical", "emotional"]` → 路由到 Expert，Expert prompt 里加情绪安抚前缀

### 食物照片 → 饮食打卡设计意图

- 用户上传食物照片 = 同时完成两件事：
  1. 给 Expert Agent 提供饮食信息（medical 路径）
  2. 自动触发 `task_trigger`（通知 Task Agent：今日饮食打卡完成）
- 药物照片不触发 task_trigger
- **待确认（Bailey）**：triage 对食物图片是否会返回 `["medical", "task"]`
- `task_trigger` 格式暂时保持现有结构，待和 Chayi 对齐后调整

### task_trigger 当前格式

```python
{"user_id": "...", "timestamp": "...", "request": "...", "type": "task_request"}
```

未来可能需要加 `event_type` 字段（如 `"food_uploaded"`），待和 Chayi 约定。
