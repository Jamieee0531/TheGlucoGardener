# PRD: Health Companion Chatbot

> 版本: v0.3 | 日期: 2026-03-13 | 作者: Jamie & Bailey

---

## 一、概述

Health Companion 是面向新加坡糖尿病患者的多模态聊天 Agent，支持文字、语音、图片输入，通过意图分类 + 情绪感知路由到专业 Agent。

---

## 二、系统架构

### LangGraph 图流程

```
input_node → glucose_reader → triage_node → policy_node
  → [条件路由] → Agent → history_update → END
```

### 节点说明

| 节点 | 职责 | 是否调 LLM |
|------|------|-----------|
| input_node | 处理三种输入：文字直通、语音→MERaLiON 转写+情绪、图片→Vision Agent 识别 | 否（调外部服务） |
| glucose_reader | 读取共享数据库最近 1 小时血糖数据（最近 6 条 raw value），注入 state | 否 |
| triage_node | 意图分类（关键词预分类 + LLM 兜底）+ 情绪判断 + **心理危机检测** | 条件调（关键词没命中时） |
| policy_node | 生成情绪上下文描述供 agent 参考，记录近 5 轮负面情绪 | 否 |
| expert_agent | 慢性病医疗顾问，单轮回答（数据预注入 + RAG，无追问链） | 是（SEA-LION 70B） |
| companion_agent | 情绪陪伴 | 是（SEA-LION 32B） |
| chitchat_agent | 日常闲聊 | 是（SEA-LION 32B） |
| history_update | 本轮对话追加到 history，由 checkpointer 持久化 | 否 |

### 路由规则

```
intent → Agent 映射：
  medical   → expert_agent
  emotional → companion_agent
  chitchat  → chitchat_agent
```

意图由 triage 决定，支持多意图（all_intents），路由取第一个。
不再识别 task 意图，任务由 Task Agent 内部生成和管理。

---

## 三、意图分类（Triage）

### 两级策略

1. **关键词预分类**（优先级：medical > emotional）
   - medical: 血糖/glucose/药/medicine/饮食/diet/GI...
   - emotional: 难过/焦虑/压力/stress/depressed...
   - 命中 → 跳过 LLM，直接返回

2. **LLM 兜底**（关键词没命中时）
   - 调 SEA-LION，只对用户当前输入进行意图识别（不处理 system prompt / 历史摘要）
   - 返回 `{"intents": ["medical", "emotional"]}` 格式
   - 纯礼貌词（谢谢/好的/嗯）→ chitchat

### 情绪判断

统一阈值 0.6，不做文字关键词情绪识别：

- 语音模式 + confidence ≥ 0.6 → 用 MERaLiON 结果
- 语音模式 + confidence < 0.6 → neutral
- 文字模式 → 一律 neutral
- 情绪**不走 LLM**，只用语音模型

### 心理危机检测（在 triage 层）

每条消息都做正则匹配，不管最终路由到哪个 agent 都能兜住：

```python
_CRISIS_PATTERNS = [
    r"活着.*没.*意思", r"不想.*活", r"去死", r"伤害.*自己", r"结束.*生命",
    r"no\s*point\s*living", r"want\s*to\s*die", r"hurt\s*myself", r"end\s*my\s*life",
]
```

命中 → 立即输出危机热线（SOS 1-767 / IMH 6389 2222）+ 触发 alert_trigger 给 Julia 预警模块。

---

## 四、情绪数据存储

Chatbot 只负责**存入**情绪数据，不负责触发下游逻辑（Julia 的 Alert Agent 自己读取判断）。

### 三层存储设计

| 表 | 字段 | 写入时机 | 生命周期 |
|----|------|---------|---------|
| `latest_emotion` | emotion_label, updated_at | 语音输入 + confidence ≥ 0.6 | 覆盖写，Julia 读时判 2 小时有效期 |
| `daily_emotion_log` | emotion_label, user_input, timestamp | 语音 + confidence ≥ 0.6 且非 neutral 才存（文字输入不写） | 当天有效，23:59 汇总后可删 |
| `emotion_summary` | text, emotion, date | 每天 23:59 定时任务，根据当日 daily_emotion_log 调 LLM 汇总 | 永久保留 |

### 数据流

```
语音输入 → MERaLiON → emotion_label + confidence
  ├─ confidence ≥ 0.6 → 采信，写 latest_emotion 表（覆盖）+ state.emotion_label = 结果
  │                      └─ 非 neutral → 写 daily_emotion_log 表
  └─ confidence < 0.6 → state.emotion_label = neutral，不写任何表

文字输入 → state.emotion_label = neutral，不写任何表

每天 23:59 → 读 daily_emotion_log → LLM 汇总 → 写 emotion_summary 表 → 清空当日 log
```

### 当前实现状态

- [x] `latest_emotion`：已实现（Bailey 的 emotion_log 表 + upsert_emotion_log）
- [ ] `daily_emotion_log`：待实现
- [ ] `emotion_summary` 每日定时汇总：待实现（当前是 companion 遇负面情绪立刻存，需改为每日汇总）

---

## 五、专家 Agent（Expert）

### 核心设计：单轮 + 数据预注入

不做多轮追问。所有数据在进入 expert 前已就绪：

| 数据来源 | 注入方式 | 示例 |
|---------|---------|------|
| 当前血糖 | glucose_reader 读共享数据库最近 1 小时（6 条 raw value） | "07:30 血糖 6.8 mmol/L" |
| 当前饮食 | 用户本轮发图片 → Vision Agent 识别结果（state，不存 DB） | "Hainanese Chicken Rice, 500kcal" |
| 情绪 | triage + policy | "用户当前情绪：anxious" |
| 血糖趋势 | expert 自己读共享数据库近 7 天**每日浓缩**（非 raw value） | "3/12：空腹 6.8, 餐后峰 10.3, 均值 8.1" |
| 历史饮食 | expert 自己读共享数据库近 7 天饮食记录（Task Agent 存的） | 近 7 天三餐记录 |
| 情绪趋势 | expert 自己读 emotion_summary 近 14 天 | 近两周情绪走势 |
| 知识 | RAG 检索（关键词触发） | 糖尿病管理、药物、SG 食物 |

**注意**：血糖每日浓缩由数据库端提供（每日汇总字段），chatbot 不负责生成。

### RAG 知识库

3 个本地知识文件，关键词触发检索（不是每轮都查）：
- `diabetes_management.txt` — 糖尿病管理指南
- `medications.txt` — 常用药物信息
- `sg_foods.txt` — 新加坡本地食物

---

## 六、陪伴 Agent（Companion）

- 情绪支持，像朋友聊天，回复 60 字以内
- 不提供具体医疗建议
- 读取 emotion_summary 近 14 天注入 prompt，了解患者近期情绪背景

---

## 七、数据读写职责

### Chatbot 写入（只写情绪）

| 表 | 写入内容 |
|----|---------|
| latest_emotion | 最新语音情绪 |
| daily_emotion_log | 每轮非 neutral 情绪 + 输入 |
| emotion_summary | 每日情绪汇总 |

### Chatbot 读取（从共享数据库）

| 数据 | 读取位置 | 读取时机 |
|------|---------|---------|
| 血糖（1h raw） | 共享 DB 血糖表 | glucose_reader，每条消息 |
| 血糖（7天浓缩） | 共享 DB 血糖每日汇总 | expert_agent 内部 |
| 饮食（7天历史） | 共享 DB 饮食表（Task Agent 存的） | expert_agent 内部 |
| emotion_summary | chatbot 自己的表 | companion_agent / expert_agent 内部 |
| 用户档案 | 共享 DB 用户表 | 每次 session |

### 与其他模块的交互

```
Chatbot 只存情绪，只读其他数据
Task Agent 自己管任务 + 存饮食记录，chatbot 不触发
Alert Agent (Julia) 自己读 latest_emotion + emotion_summary，chatbot 不触发
唯一主动触发：心理危机检测 → alert_trigger → Julia
```

---

## 八、技术选型

| 层面 | 选型 |
|------|------|
| 编排框架 | LangGraph（StateGraph + 条件路由） |
| 对话模型 | SEA-LION Qwen-32B-IT |
| 推理模型 | SEA-LION Llama-70B-R（expert agent） |
| 视觉模型 | Gemini 2.5 Flash（Vision Agent） |
| 语音处理 | MERaLiON（ASR + SER，无 key 时 mock） |
| 数据持久化 | SQLite（情绪三个表 + LangGraph checkpointer） |
| RAG | ChromaDB + 本地知识文件 |
| Vision 集成 | 直接 import（同 repo） |

---

## 九、待完成项

| 项目 | 优先级 | 说明 |
|------|--------|------|
| daily_emotion_log + 每日汇总 | P1 | 情绪三层存储的后两层 |
| 心理危机检测移到 triage | P1 | 当前在 companion，需移到 triage 层全局覆盖 |
| device_sync → glucose_reader | P1 | 重命名 + 去掉用药读取，只读 1h 血糖 |
| 去掉 task_forward 节点 | P1 | 删除 task 意图识别 + task_forward 节点 |
| expert 读共享 DB | P2 | 替换 health_events 读取为直接读共享 DB（血糖浓缩 + 饮食历史） |
| 限流降级 | P3 | SEA-LION 6 次/分钟限制，需要降级策略 |

---

## 附录

### 模块间数据流

```
用户输入（文字/语音/图片）
  │
  ├─ [语音] → MERaLiON → 转写文字 + emotion_label
  │                        └─ ≥0.5 → 写 latest_emotion 表
  ├─ [图片] → Vision Agent → 结构化 JSON（当前上下文用，不存 DB）
  │
  ▼
input_node → glucose_reader（读 1h 血糖）→ triage（意图+情绪+危机检测）→ policy（情绪上下文）
  │
  ├─ medical   → expert_agent（单轮，数据预注入+RAG）
  ├─ emotional → companion_agent（陪伴）
  └─ chitchat  → chitchat_agent
  │
  ▼
history_update → END
  │
  └─ 非 neutral → 写 daily_emotion_log
  └─ 23:59 → LLM 汇总 → emotion_summary
```

### 相关文档

- Vision Agent PRD: `PRD-visionAgent.md`
