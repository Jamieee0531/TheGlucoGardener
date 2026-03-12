# CLAUDE.md - Multimodal Vision Agent

## ⚠️ 当前分支说明（practice branch）

**这个分支（`practice`）不是用来开发功能的。**
Jamie 在这里练习从网上学到的 AI coding 技巧和实验性工作流。
代码改动随时可能发生，目的是练手，不代表正式功能方向。
主项目代码在 `master` 分支。

---

## Project Overview

**项目**: SG INNOVATION 比赛 - AI 慢病管理与社区平台
**模块**: 多模态 Vision Agent（图片输入与处理）
**框架**: LangGraph + Python
**VLM**: Gemini 2.5 Flash（当前）；后续计划集成 FoodAI API 替换/优化食物场景识别
**核心目标**: 将非结构化的图片转化为可计算的结构化数据

## 产品定位（2026-02-25 更新）

面向新加坡慢病患者（如 2型糖尿病）的 AI 管理平台，Vision Agent 是其多模态 chatbot 的**图片处理模块**，不是独立产品。

**做什么**: 图片识别 → 提取关键信息 → 输出结构化 JSON，供主 LLM 使用

**不做什么**:
- 不生成文字建议（那是主 LLM / chatbot 的职责）
- 不处理数据库存储（那是 chatbot 模块的职责）

> 路线图与技术决策见 `findings.md`，执行进度见 `task_plan.md`

### 业务场景

1. **饮食打卡分析** - 三餐照片 → 识别食物（侧重新加坡本地） → 营养数据
2. **药物/处方核查** - 药盒/处方单/胰岛素笔 → 药名、剂量、频次
3. **医疗报告数字化** - 纸质化验单 → 关键指标（HbA1c、血糖值等）

### 技术选型

- **编排框架**: LangGraph（状态图 + 节点 + 条件边）
- **VLM**: SEA-LION API（主办方提供接入方式，后续对接）
  - 开发阶段使用抽象接口 + mock，确保模型可替换
- **数据校验**: Pydantic v2（结构化输出定义）
- **语言**: Python 3.11+
- **虚拟环境**: venv（项目根目录 .venv/）

### 团队分工

本仓库只负责 Vision Agent 模块。其他模块（社交、任务系统、护理 Agent 等）由其他成员开发。

---

## LangGraph Architecture（初始雏形，后续可调整）

> 以下架构是初始设计，随着开发推进会持续迭代调整。

### 核心概念

```
State（状态）→ Nodes（节点）→ Edges（边/路由）
```

### Graph 流程

```
[START]
   ↓
[image_intake]     ← 接收图片，转 base64，基本校验
   ↓
[scene_classifier] ← 判断场景：FOOD / MEDICATION / REPORT / UNKNOWN
   ↓ (conditional edge)
   ├── FOOD       → [food_analyzer]       ← 识别食物，估算营养
   ├── MEDICATION → [medication_reader]    ← 提取药物信息
   ├── REPORT     → [report_digitizer]     ← 提取化验指标
   └── UNKNOWN    → [rejection_handler]    ← 非目标图片，拒识
   ↓
[output_formatter] ← 统一格式化输出 + 校验
   ↓
[END]
```

### State 定义（初始版本）

```python
class VisionAgentState(TypedDict):
    image_path: str                    # 输入图片路径
    image_base64: str                  # base64 编码
    scene_type: str                    # FOOD / MEDICATION / REPORT / UNKNOWN
    confidence: float                  # 分类置信度
    raw_response: str                  # VLM 原始返回
    structured_output: dict            # 解析后的结构化数据
    error: Optional[str]               # 错误信息
```

### Nodes = 处理函数

每个 node 是一个 Python 函数，接收 State，返回更新后的 State 部分。

### Tools（可选，后续扩展）

LangGraph 支持给 node 绑定 tools。后续可以加：
- 营养数据库查询 tool
- OCR 增强 tool
- 药物数据库查询 tool

---

## Project Structure（初始雏形，后续可调整）

```
SG_INNOVATION/
├── CLAUDE.md
├── plan.md                              # 项目计划（只读参考）
├── github-Multi-Agent-Medical-Assistant.md
├── Multi-Agent-Medical-Assistant/       # 参考项目（只读，不修改）
│
├── .venv/                               # Python 虚拟环境（不提交）
├── .env.example                         # 环境变量模板
├── .gitignore
├── requirements.txt
│
├── src/
│   └── vision_agent/
│       ├── __init__.py
│       ├── graph.py                     # LangGraph 图定义（核心入口）
│       ├── state.py                     # State 类型定义
│       ├── nodes/                       # 各节点实现
│       │   ├── __init__.py
│       │   ├── image_intake.py          # 图片接收与预处理
│       │   ├── scene_classifier.py      # 场景分类
│       │   ├── food_analyzer.py         # 饮食分析
│       │   ├── medication_reader.py     # 药物识别
│       │   ├── report_digitizer.py      # 报告数字化
│       │   ├── rejection_handler.py     # 拒识处理
│       │   └── output_formatter.py      # 输出格式化
│       ├── prompts/                     # Prompt 模板（核心工作量）
│       │   ├── __init__.py
│       │   ├── classifier.py            # 场景分类 prompt
│       │   ├── food.py                  # 饮食分析 prompt
│       │   ├── medication.py            # 药物识别 prompt
│       │   └── report.py               # 报告数字化 prompt
│       ├── schemas/                     # Pydantic 输出模型
│       │   ├── __init__.py
│       │   └── outputs.py              # 各场景的输出结构
│       └── llm/                         # LLM/VLM 接口层
│           ├── __init__.py
│           ├── base.py                  # 抽象基类
│           ├── sealion.py               # SEA-LION 实现（后续）
│           └── mock.py                  # Mock 实现（开发阶段）
│
├── tests/
│   ├── __init__.py
│   ├── test_graph.py
│   ├── test_nodes/
│   └── test_schemas/
│
└── test_images/                         # 测试图片
```

---

## Development Guidelines

### 代码规范

- PEP 8 + type hints
- 函数 <50 行，文件 <400 行（上限 800）
- 不可变数据模式
- 每个 node 函数职责单一

### Prompt 管理

Prompt Engineering 是本项目的核心工作量：
- 每个场景的 prompt 独立文件管理
- prompt 中要约束输出为严格 JSON 格式
- 针对新加坡本地食物/药物做专门优化

### Git 规范

- Commit: `<type>: <description>` (feat/fix/refactor/docs/test/chore)
- 不提交: `.env`、`.venv/`、API keys、敏感医疗数据

### 关键原则

1. **模型可替换** - 抽象接口，SEA-LION 只是一个实现
2. **只做 Vision** - 不涉及其他模块
3. **参考项目只读** - 不修改 Multi-Agent-Medical-Assistant/
4. **架构灵活** - 当前结构是初始雏形，随开发迭代调整

---

## Reference Project

`Multi-Agent-Medical-Assistant/` 可借鉴的模式：
- LangGraph 状态图编排 (`agent_decision.py`)
- 图片转 base64 + Vision API 调用 (`image_classifier.py`)
- TypedDict/Pydantic 约束 JSON 输出
- Agent 包装类的组织结构
- 错误处理和日志模式

详细笔记见 `github-Multi-Agent-Medical-Assistant.md`
