# Chatbot Integration + Enhancement Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate Vision Agent into Health-Companion chatbot, refactor Expert Agent to state-driven with confidence, optimize triage, and validate via demo golden path.

**Architecture:** Extend Bailey's existing LangGraph flow by modifying `input_node` to handle images via direct import of Vision Agent. Refactor Expert Agent from fixed-order to confidence-driven state machine. Add keyword pre-classification to triage.

**Tech Stack:** Python 3.11+, LangGraph, Pydantic v2, Vision Agent (Gemini 2.5 Flash), SEA-LION (Qwen-32B-IT / Llama-70B-R)

**Working Directory:** `/Users/jamie/Documents/Python_Basic_Study/SG-INNOVATION/Health-Companion/`

**Vision Agent Path:** `/Users/jamie/Documents/Python_Basic_Study/SG-INNOVATION/SG_INNOVATION/`

---

## Task 1: Extend ChatState for Vision

**Files:**
- Modify: `state/chat_state.py`
- Test: `tests/test_chat_state.py` (create)

**Step 1: Create tests directory and test file**

```bash
mkdir -p tests
```

```python
# tests/test_chat_state.py
from state.chat_state import ChatState


def test_chat_state_has_vision_fields():
    """ChatState should accept image_paths and vision_result fields."""
    state = ChatState(
        user_input="test",
        input_mode="text",
        chat_mode="personal",
        user_id="u1",
        history=[],
        user_profile={},
        image_paths=["/tmp/food.jpg"],
        vision_result=[{"scene_type": "FOOD", "confidence": 0.9}],
    )
    assert state["image_paths"] == ["/tmp/food.jpg"]
    assert state["vision_result"][0]["scene_type"] == "FOOD"


def test_chat_state_vision_fields_default_empty():
    """Vision fields should default to None when not provided."""
    state = ChatState(
        user_input="hello",
        input_mode="text",
        chat_mode="personal",
        user_id="u1",
        history=[],
        user_profile={},
    )
    assert state.get("image_paths") is None
    assert state.get("vision_result") is None
```

**Step 2: Run test to verify it fails**

```bash
cd /Users/jamie/Documents/Python_Basic_Study/SG-INNOVATION/Health-Companion
python -m pytest tests/test_chat_state.py -v
```

Expected: FAIL (image_paths/vision_result not in ChatState)

**Step 3: Add vision fields to ChatState**

Add these fields to `state/chat_state.py`:

```python
    # ── 图片 / Vision Agent ────────────────────────────────
    image_paths:    Optional[list]    # 用户发送的图片路径列表
    vision_result:  Optional[list]    # Vision Agent 识别结果列表
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_chat_state.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add state/chat_state.py tests/test_chat_state.py
git commit -m "feat: add vision fields to ChatState"
```

---

## Task 2: input_node Handles Images

**Files:**
- Modify: `agents/triage.py` (input_node function)
- Test: `tests/test_input_node.py` (create)

**Context:** The current `input_node` handles text and voice. We extend it to handle images. When images are present, call Vision Agent and store results. If no text accompanies the image, generate a synthetic text based on scene_type.

**Step 1: Write the failing test**

```python
# tests/test_input_node.py
"""Test input_node image handling with mock Vision Agent."""
import sys
import os
from unittest.mock import patch, MagicMock
from state.chat_state import ChatState


def _make_state(**overrides):
    """Helper to create a minimal ChatState."""
    defaults = dict(
        user_input="",
        input_mode="text",
        chat_mode="personal",
        user_id="u1",
        history=[],
        user_profile={},
        image_paths=None,
        vision_result=None,
    )
    defaults.update(overrides)
    return ChatState(**defaults)


def test_input_node_text_only_unchanged():
    """Text-only input should pass through without calling Vision Agent."""
    from agents.triage import input_node

    state = _make_state(user_input="hello", image_paths=None)
    result = input_node(state)
    assert result.get("vision_result") is None or result.get("vision_result") == []
    assert "transcribed_text" in result


def test_input_node_image_calls_vision_agent():
    """Image input should call Vision Agent and store result."""
    from agents.triage import input_node

    mock_result = MagicMock()
    mock_result.scene_type = "FOOD"
    mock_result.confidence = 0.85
    mock_result.structured_output = MagicMock()
    mock_result.structured_output.model_dump.return_value = {
        "scene_type": "FOOD",
        "items": [{"name": "Chicken Rice"}],
        "confidence": 0.85,
    }
    mock_result.is_error = False

    with patch("agents.triage.analyze_image", return_value=mock_result):
        state = _make_state(
            user_input="",
            image_paths=["/tmp/food.jpg"],
        )
        result = input_node(state)

    assert result["vision_result"] is not None
    assert len(result["vision_result"]) == 1
    assert result["vision_result"][0]["scene_type"] == "FOOD"


def test_input_node_image_no_text_generates_synthetic():
    """Image with no text should generate synthetic user_input."""
    from agents.triage import input_node

    mock_result = MagicMock()
    mock_result.scene_type = "FOOD"
    mock_result.confidence = 0.85
    mock_result.structured_output = MagicMock()
    mock_result.structured_output.model_dump.return_value = {
        "scene_type": "FOOD",
        "confidence": 0.85,
    }
    mock_result.is_error = False

    with patch("agents.triage.analyze_image", return_value=mock_result):
        state = _make_state(user_input="", image_paths=["/tmp/food.jpg"])
        result = input_node(state)

    # Should generate text like "我拍了一张食物照片"
    assert result["user_input"] != ""
    assert "食物" in result["user_input"] or "food" in result["user_input"].lower()


def test_input_node_image_with_text_keeps_original():
    """Image with text should keep original user_input."""
    from agents.triage import input_node

    mock_result = MagicMock()
    mock_result.scene_type = "MEDICATION"
    mock_result.confidence = 0.9
    mock_result.structured_output = MagicMock()
    mock_result.structured_output.model_dump.return_value = {
        "scene_type": "MEDICATION",
        "confidence": 0.9,
    }
    mock_result.is_error = False

    with patch("agents.triage.analyze_image", return_value=mock_result):
        state = _make_state(
            user_input="this is my medicine",
            image_paths=["/tmp/med.jpg"],
        )
        result = input_node(state)

    assert result.get("user_input", "this is my medicine") == "this is my medicine"
    assert result["vision_result"] is not None
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_input_node.py -v
```

Expected: FAIL (analyze_image not defined, input_node doesn't handle images)

**Step 3: Implement image handling in input_node**

In `agents/triage.py`, add the Vision Agent import wrapper and modify `input_node`:

```python
# At top of agents/triage.py, add:
import sys
import os

# Add Vision Agent to path for direct import
_VISION_AGENT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "SG_INNOVATION"
)
if os.path.isdir(_VISION_AGENT_PATH) and _VISION_AGENT_PATH not in sys.path:
    sys.path.insert(0, _VISION_AGENT_PATH)


def analyze_image(image_path):
    """Wrapper: call Vision Agent to analyze an image.

    Returns an AnalysisResult from vision_agent.agent.
    """
    from src.vision_agent.agent import VisionAgent
    agent = VisionAgent()  # MockVLM by default; swap for Gemini in production
    return agent.analyze(image_path)


# Scene type → synthetic text mapping
SCENE_TEXT_MAP = {
    "FOOD":       "我拍了一张食物照片",
    "MEDICATION": "我拍了一张药物照片",
    "REPORT":     "我拍了一张化验单照片",
    "UNKNOWN":    "我发了一张照片",
}
```

Then modify `input_node`:

```python
def input_node(state: ChatState) -> dict:
    # ── Voice mode ──────────────────────────────────────
    if state["input_mode"] == "voice":
        audio_path = state.get("audio_path", "")
        result = process_voice_input(audio_path)
        return {
            "user_input":         result["transcribed_text"],
            "transcribed_text":   result["transcribed_text"],
            "emotion_label":      result["emotion_label"],
            "emotion_confidence": result["emotion_confidence"],
        }

    # ── Image handling ──────────────────────────────────
    image_paths = state.get("image_paths") or []
    vision_result = []

    if image_paths:
        for path in image_paths:
            try:
                result = analyze_image(path)
                if not result.is_error and result.structured_output:
                    vision_result.append(result.structured_output.model_dump())
                else:
                    vision_result.append({
                        "scene_type": "UNKNOWN",
                        "error": result.error or "识别失败",
                        "confidence": 0.0,
                    })
            except Exception as e:
                vision_result.append({
                    "scene_type": "UNKNOWN",
                    "error": str(e),
                    "confidence": 0.0,
                })

    # ── Synthetic text for image-only input ─────────────
    user_input = state["user_input"]
    if image_paths and not user_input.strip():
        scene = vision_result[0].get("scene_type", "UNKNOWN") if vision_result else "UNKNOWN"
        user_input = SCENE_TEXT_MAP.get(scene, "我发了一张照片")

    updates = {
        "transcribed_text":   user_input,
        "emotion_label":      "neutral",
        "emotion_confidence": 0.0,
    }

    if image_paths:
        updates["user_input"] = user_input
        updates["vision_result"] = vision_result

    return updates
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_input_node.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add agents/triage.py tests/test_input_node.py
git commit -m "feat: input_node handles image via Vision Agent"
```

---

## Task 3: Expert Agent — State-Driven with Confidence

**Files:**
- Modify: `agents/expert.py`
- Test: `tests/test_expert_state.py` (create)

**Context:** Current Expert uses fixed order (idle → glucose → diet → medication → summarizing) with keyword detection. Refactor to check a state dict where each field is `empty`, `uncertain`, or `confirmed` based on Vision Agent confidence + user answers.

**Step 1: Write the failing test**

```python
# tests/test_expert_state.py
"""Test Expert Agent confidence-driven state logic."""
from agents.expert import classify_field, FieldStatus, determine_next_question


def test_classify_field_empty_when_none():
    assert classify_field(None, None) == FieldStatus.EMPTY


def test_classify_field_empty_when_low_confidence():
    assert classify_field("some value", 0.3) == FieldStatus.EMPTY


def test_classify_field_uncertain_when_mid_confidence():
    assert classify_field("some value", 0.6) == FieldStatus.UNCERTAIN


def test_classify_field_confirmed_when_high_confidence():
    assert classify_field("some value", 0.9) == FieldStatus.CONFIRMED


def test_classify_field_confirmed_when_user_provided():
    """User-provided values (confidence=None) are always confirmed."""
    assert classify_field("7.2 mmol", None) == FieldStatus.CONFIRMED


def test_determine_next_question_asks_glucose_first():
    collected = {"glucose": None, "diet": None, "medication": None}
    field, status = determine_next_question(collected)
    assert field == "glucose"
    assert status == FieldStatus.EMPTY


def test_determine_next_question_skips_confirmed():
    collected = {
        "glucose": {"value": "7.2", "confidence": 0.9},
        "diet": {"value": "Chicken Rice", "confidence": 0.85},
        "medication": None,
    }
    field, status = determine_next_question(collected)
    assert field == "medication"
    assert status == FieldStatus.EMPTY


def test_determine_next_question_confirms_uncertain():
    collected = {
        "glucose": {"value": "7.2", "confidence": 0.9},
        "diet": {"value": "Chicken Rice", "confidence": 0.6},
        "medication": None,
    }
    field, status = determine_next_question(collected)
    assert field == "diet"
    assert status == FieldStatus.UNCERTAIN


def test_determine_next_question_all_confirmed():
    collected = {
        "glucose": {"value": "7.2", "confidence": 0.9},
        "diet": {"value": "Chicken Rice", "confidence": 0.85},
        "medication": {"value": "Metformin 500mg", "confidence": 0.9},
    }
    field, status = determine_next_question(collected)
    assert field is None  # All confirmed → ready for summary
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_expert_state.py -v
```

Expected: FAIL (FieldStatus, classify_field, determine_next_question not defined)

**Step 3: Implement confidence-driven state logic**

Refactor `agents/expert.py`. Keep the LLM call structure, replace `_detect_next_stage` with confidence-driven logic:

```python
"""
专家Agent，用Llama推理模型
State-driven: 根据 collected_info 中各字段的置信度决定追问/确认/跳过
接收 policy 指令 + vision_result 自动填充已知信息
"""
from datetime import datetime
from enum import Enum
from state.chat_state import ChatState
from utils.llm_factory import call_sealion_with_history, format_history_for_sealion


class FieldStatus(str, Enum):
    EMPTY = "empty"           # No value, or confidence < 0.5
    UNCERTAIN = "uncertain"   # Has value, confidence 0.5~0.8
    CONFIRMED = "confirmed"   # Has value, confidence >= 0.8, or user-provided


# Confidence thresholds (from docs/roadmap.md)
CONFIDENCE_LOW = 0.5
CONFIDENCE_HIGH = 0.8

# Fields the Expert needs to collect, in priority order
REQUIRED_FIELDS = ["glucose", "diet", "medication"]


def classify_field(value, confidence):
    """Classify a collected field's status based on value and confidence."""
    if value is None:
        return FieldStatus.EMPTY
    # User-provided values have no confidence score → always confirmed
    if confidence is None:
        return FieldStatus.CONFIRMED
    if confidence < CONFIDENCE_LOW:
        return FieldStatus.EMPTY
    if confidence < CONFIDENCE_HIGH:
        return FieldStatus.UNCERTAIN
    return FieldStatus.CONFIRMED


def determine_next_question(collected):
    """Find the next field that needs attention.

    Returns (field_name, status) or (None, None) if all confirmed.
    Priority: uncertain fields first (need confirmation), then empty fields.
    """
    # First pass: find uncertain fields (need confirmation)
    for field in REQUIRED_FIELDS:
        entry = collected.get(field)
        if entry is None:
            continue
        value = entry.get("value") if isinstance(entry, dict) else entry
        conf = entry.get("confidence") if isinstance(entry, dict) else None
        status = classify_field(value, conf)
        if status == FieldStatus.UNCERTAIN:
            return field, status

    # Second pass: find empty fields
    for field in REQUIRED_FIELDS:
        entry = collected.get(field)
        if entry is None:
            return field, FieldStatus.EMPTY
        value = entry.get("value") if isinstance(entry, dict) else entry
        conf = entry.get("confidence") if isinstance(entry, dict) else None
        status = classify_field(value, conf)
        if status == FieldStatus.EMPTY:
            return field, status

    return None, None


def _prefill_from_vision(collected, vision_result):
    """Pre-fill collected_info from Vision Agent results."""
    if not vision_result:
        return collected

    collected = dict(collected)  # Don't mutate original

    for result in vision_result:
        scene = result.get("scene_type", "")
        confidence = result.get("confidence", 0.0)

        if scene == "FOOD" and collected.get("diet") is None:
            items = result.get("items", [])
            if items:
                food_names = ", ".join(item.get("name", "") for item in items)
                total_cal = result.get("total_calories_kcal", "")
                collected["diet"] = {
                    "value": f"{food_names} (约{total_cal}大卡)",
                    "confidence": confidence,
                    "source": "vision",
                }

        elif scene == "MEDICATION" and collected.get("medication") is None:
            drug = result.get("drug_name", "")
            dosage = result.get("dosage", "")
            collected["medication"] = {
                "value": f"{drug} {dosage}".strip(),
                "confidence": confidence,
                "source": "vision",
            }

    return collected


def _build_question_prompt(field, status, collected, name):
    """Build the stage instruction based on which field needs attention."""
    if field == "glucose" and status == FieldStatus.EMPTY:
        return f"先用一句话表示关心，然后只问：{name}，您的血糖大概测到多少呢？不要给任何建议。"

    if field == "diet" and status == FieldStatus.EMPTY:
        return f"先回应一句，然后只问：今天吃了什么？不要给任何建议。"

    if field == "diet" and status == FieldStatus.UNCERTAIN:
        value = collected["diet"]["value"] if isinstance(collected["diet"], dict) else collected["diet"]
        return f"向用户确认：看起来您吃的是{value}，对吗？不要给建议，等用户确认。"

    if field == "medication" and status == FieldStatus.EMPTY:
        return f"先回应饮食情况（一句话），然后只问：今天的药有按时服用吗？不要给任何建议。"

    if field == "medication" and status == FieldStatus.UNCERTAIN:
        value = collected["medication"]["value"] if isinstance(collected["medication"], dict) else collected["medication"]
        return f"向用户确认：看起来您在服用{value}，对吗？不要给建议，等用户确认。"

    # All confirmed → summarize
    return _build_summary_prompt(collected, name)


def _build_summary_prompt(collected, name):
    """Build the final summary instruction."""
    def _val(entry):
        if isinstance(entry, dict):
            return entry.get("value", "未知")
        return entry or "未知"

    return f"""信息已齐全，给出综合建议：
- 血糖：{_val(collected.get('glucose'))}
- 饮食：{_val(collected.get('diet'))}
- 用药：{_val(collected.get('medication'))}
结合新加坡本地饮食文化给出具体建议。末尾加免责声明。"""


def _update_collected_from_user(user_input, field, collected):
    """When user answers a question, store their answer as confirmed."""
    collected = dict(collected)
    collected[field] = {"value": user_input, "confidence": None, "source": "user"}
    return collected


def expert_agent_node(state: ChatState) -> dict:
    profile     = state.get("user_profile", {})
    name        = profile.get("name", "患者")
    language    = profile.get("language", "Chinese")
    conditions  = profile.get("conditions", ["Type 2 Diabetes"])
    medications = profile.get("medications", [])
    all_intents = state.get("all_intents", ["medical"])

    collected = dict(state.get("collected_info") or {})
    current_stage = state.get("conversation_stage") or "idle"

    # ── Pre-fill from Vision Agent results ──────────────
    vision_result = state.get("vision_result") or []
    collected = _prefill_from_vision(collected, vision_result)

    # ── If user was answering a question, store their answer ──
    if current_stage != "idle" and state["user_input"].strip():
        # Map stage to field being asked
        stage_field_map = {
            "asking_glucose": "glucose",
            "asking_diet": "diet",
            "asking_medication": "medication",
            "confirming_diet": "diet",
            "confirming_medication": "medication",
        }
        asked_field = stage_field_map.get(current_stage)
        if asked_field:
            collected = _update_collected_from_user(
                state["user_input"], asked_field, collected
            )

    # ── Determine what to ask/confirm/summarize ─────────
    next_field, next_status = determine_next_question(collected)

    if next_field is None:
        # All confirmed → summarize
        stage_instruction = _build_summary_prompt(collected, name)
        next_stage = "idle"  # Reset after summary
    else:
        stage_instruction = _build_question_prompt(
            next_field, next_status, collected, name
        )
        if next_status == FieldStatus.UNCERTAIN:
            next_stage = f"confirming_{next_field}"
        else:
            next_stage = f"asking_{next_field}"

    # ── Emotional prefix ────────────────────────────────
    emotional_prefix = ""
    if "emotional" in all_intents or state.get("emotion_label") in ["anxious", "sad", "angry"]:
        emotional_prefix = "先用一句话安抚用户情绪，再进行追问或给建议。\n"

    # ── Task trigger ────────────────────────────────────
    task_suffix = ""
    task_trigger = None
    if "task" in all_intents:
        task_suffix = "\n最后提醒用户：打卡任务已转给任务系统处理。"
        task_trigger = {
            "user_id": state["user_id"],
            "timestamp": datetime.now().isoformat(),
            "request": state["user_input"],
            "type": "task_request",
        }

    # ── Alert trigger (glucose check) ──────────────────
    alert_trigger = None
    glucose_entry = collected.get("glucose")
    if glucose_entry and next_field is None:
        # All info collected, check if glucose is elevated
        glucose_val = glucose_entry.get("value", "") if isinstance(glucose_entry, dict) else str(glucose_entry)
        import re
        numbers = re.findall(r'\d+\.?\d*', glucose_val)
        if numbers:
            glucose_num = float(numbers[0])
            if glucose_num > 7.0 or glucose_num < 3.9:
                alert_trigger = {
                    "user_id": state["user_id"],
                    "timestamp": datetime.now().isoformat(),
                    "glucose_value": glucose_num,
                    "severity": "elevated" if glucose_num > 7.0 else "low",
                }
                print(f"[Expert] Alert trigger: glucose {glucose_num}")

    # ── Policy instruction ──────────────────────────────
    policy_instruction = state.get("policy_instruction", "正常进行追问和建议。")

    system_prompt = f"""你是专业的慢性病管理医疗顾问，专注于新加坡患者。
患者：{name} | 病症：{', '.join(conditions)} | 用药：{', '.join(medications) if medications else '未记录'}
请用{language}回复。

【当前策略指令】
{policy_instruction}

{emotional_prefix}{stage_instruction}

通用规则：
- "打卡"指健康任务打卡，不是自我伤害
- 结合新加坡本地饮食文化
- 回复150字以内{task_suffix}"""

    history = format_history_for_sealion(state.get("history", []))
    history.append({"role": "user", "content": state["user_input"]})
    response = call_sealion_with_history(system_prompt, history, reasoning=True)

    if "</think>" in response:
        response = response.split("</think>")[-1].strip()

    print(f"[Expert] Stage: {current_stage} -> {next_stage} | Next: {next_field}")
    return {
        "response": response,
        "conversation_stage": next_stage,
        "collected_info": collected,
        "task_trigger": task_trigger,
        "alert_trigger": alert_trigger,
    }
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_expert_state.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add agents/expert.py tests/test_expert_state.py
git commit -m "feat: refactor Expert Agent to confidence-driven state machine"
```

---

## Task 4: Triage — Keyword Pre-Classification

**Files:**
- Modify: `agents/triage.py` (_full_triage function)
- Test: `tests/test_triage.py` (create)

**Context:** Add keyword-based pre-classification before LLM call. If keywords clearly match an intent, use that directly (saves tokens and latency). Fall back to LLM for ambiguous cases.

**Step 1: Write the failing test**

```python
# tests/test_triage.py
"""Test triage keyword pre-classification."""
from agents.triage import keyword_preclassify


def test_medical_keywords():
    assert keyword_preclassify("我血糖有点高") == "medical"
    assert keyword_preclassify("吃了药") == "medical"


def test_alert_keywords():
    assert keyword_preclassify("我头好晕快晕倒了") == "alert"
    assert keyword_preclassify("血糖测到 16 了") == "alert"


def test_emotional_keywords():
    assert keyword_preclassify("我好难过") == "emotional"
    assert keyword_preclassify("最近压力好大") == "emotional"


def test_task_keywords():
    assert keyword_preclassify("帮我打卡") == "task"


def test_ambiguous_returns_none():
    """Ambiguous input should return None (fall back to LLM)."""
    assert keyword_preclassify("今天天气不错") is None
    assert keyword_preclassify("你好") is None
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_triage.py -v
```

Expected: FAIL (keyword_preclassify not defined)

**Step 3: Implement keyword_preclassify**

Add to `agents/triage.py`:

```python
# Keyword pre-classification rules (checked before LLM)
KEYWORD_RULES = [
    # (intent, keywords) — checked in priority order
    ("alert", ["头晕", "晕倒", "胸痛", "发抖", "chest pain", "dizzy", "faint",
               "血糖.*1[5-9]", "血糖.*[2-9][0-9]", "血糖.*[0-2]\\.\\d", "低血糖"]),
    ("medical", ["血糖", "glucose", "sugar", "药", "medicine", "metformin",
                 "二甲双胍", "饮食", "diet", "吃了什么", "GI", "升糖"]),
    ("emotional", ["难过", "伤心", "压力", "焦虑", "害怕", "lonely", "stress",
                   "担心", "不开心", "depressed", "anxious"]),
    ("task", ["打卡", "积分", "提醒我", "记录", "remind"]),
]


def keyword_preclassify(user_input: str):
    """Try to classify intent by keywords. Returns intent or None."""
    import re
    text = user_input.lower()
    for intent, keywords in KEYWORD_RULES:
        for kw in keywords:
            if re.search(kw, text):
                return intent
    return None
```

Then modify `_full_triage` to try keyword first:

```python
def _full_triage(state: ChatState) -> dict:
    """完整的意图+情绪判断：关键词预分类 + LLM兜底"""
    emotion_label      = state.get("emotion_label", "neutral")
    emotion_confidence = state.get("emotion_confidence", 0.0)
    user_input         = state["user_input"]

    # ── Step 1: Try keyword pre-classification ──────────
    keyword_intent = keyword_preclassify(user_input)

    if keyword_intent:
        # Keyword matched → still need emotion from LLM (or default)
        # For prototype: use simple emotion keywords too
        emotion = _simple_emotion_detect(user_input, emotion_label, emotion_confidence,
                                          state.get("input_mode", "text"))
        print(f"[Triage] 关键词命中：{keyword_intent} | 情绪：{emotion}")
        return {
            "intent": keyword_intent,
            "all_intents": [keyword_intent],
            "emotion_label": emotion,
        }

    # ── Step 2: Fall back to LLM ────────────────────────
    # ... (keep existing LLM triage code unchanged) ...
```

Also add simple emotion detection:

```python
EMOTION_KEYWORDS = {
    "sad": ["难过", "伤心", "不开心", "sad", "depressed"],
    "anxious": ["焦虑", "担心", "害怕", "紧张", "anxious", "worried", "压力"],
    "angry": ["生气", "烦", "angry", "frustrated"],
    "happy": ["开心", "高兴", "happy", "great"],
}


def _simple_emotion_detect(user_input, voice_emotion, voice_confidence, input_mode):
    """Simple keyword emotion detection. Voice emotion overrides if confident."""
    if input_mode == "voice" and voice_confidence > 0.6:
        return voice_emotion
    text = user_input.lower()
    for emotion, keywords in EMOTION_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return emotion
    return "neutral"
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_triage.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add agents/triage.py tests/test_triage.py
git commit -m "feat: add keyword pre-classification to triage"
```

---

## Task 5: main.py — Support Image Input

**Files:**
- Modify: `main.py`

**Context:** The CLI currently supports text and voice. Add image support: user types `image /path/to/photo.jpg` to send an image, or `image /path/to/photo.jpg some text` to send image + text.

**Step 1: Modify create_initial_state to accept image_paths**

Add `image_paths` parameter:

```python
def create_initial_state(
    user_input: str,
    user_id: str = "user_001",
    input_mode: str = "text",
    chat_mode: str = "personal",
    audio_path: str = None,
    image_paths: list = None,        # NEW
    history: list = None,
    conversation_stage: str = None,
    collected_info: dict = None,
    recent_emotions: list = None,
    persistent_alert: dict = None,
    policy_instruction: str = None,
) -> ChatState:
    return ChatState(
        # ... existing fields ...
        image_paths=image_paths,          # NEW
        vision_result=None,               # NEW — filled by input_node
    )
```

**Step 2: Add image input handling in run_cli**

In the main loop, add image detection before the standard text handling:

```python
        # 图片模式：输入 "image 图片路径" 或 "image 图片路径 附带文字"
        if user_input.lower().startswith("image "):
            parts = user_input[6:].strip().split(" ", 1)
            img_path = parts[0]
            text = parts[1] if len(parts) > 1 else ""
            print(f"[图片模式] 处理图片：{img_path}")
            state = create_initial_state(
                user_input=text,
                image_paths=[img_path],
                user_id=user_id,
                history=history,
                conversation_stage=conversation_stage,
                collected_info=collected_info,
                recent_emotions=recent_emotions,
            )
        elif user_input.lower().startswith("voice "):
            # ... existing voice handling ...
```

**Step 3: Add vision result display in output**

After the response print, add:

```python
        if result.get("vision_result"):
            for vr in result["vision_result"]:
                scene = vr.get("scene_type", "?")
                conf = vr.get("confidence", 0)
                print(f"  [Vision] {scene} (confidence: {conf:.0%})")
```

**Step 4: Test manually**

```bash
cd /Users/jamie/Documents/Python_Basic_Study/SG-INNOVATION/Health-Companion
python main.py
# Type: image /path/to/test/food.jpg
# Should see Vision Agent process the image and Expert respond
```

**Step 5: Commit**

```bash
git add main.py
git commit -m "feat: add image input support to CLI"
```

---

## Task 6: Integration Test — Golden Path

**Files:**
- Create: `tests/test_golden_path.py`

**Context:** End-to-end test of the demo golden path with mocked LLM and Vision Agent. Verifies the full flow works: image → vision → triage → policy → expert → response.

**Step 1: Write the integration test**

```python
# tests/test_golden_path.py
"""Integration test: demo golden path with mocked LLM + Vision Agent."""
from unittest.mock import patch, MagicMock
from graph.builder import build_graph
from state.chat_state import ChatState


def _mock_sealion(system_prompt, messages, reasoning=False):
    """Mock LLM that returns reasonable responses."""
    prompt_text = system_prompt + str(messages)
    if "分诊" in prompt_text or "intents" in prompt_text:
        return '{"intents": ["medical"], "emotion": "neutral"}'
    if "综合建议" in prompt_text:
        return "根据您的情况，建议控制饮食..."
    if "血糖" in prompt_text and "只问" in prompt_text:
        return "我很关心您的状况。请问您的血糖大概测到多少呢？"
    return "好的，我理解了。"


def _mock_sealion_single(system_prompt, user_message, reasoning=False):
    return _mock_sealion(system_prompt, [{"role": "user", "content": user_message}], reasoning)


@patch("agents.triage.call_sealion", side_effect=_mock_sealion_single)
@patch("utils.llm_factory.call_sealion_with_history", side_effect=_mock_sealion)
@patch("agents.expert.call_sealion_with_history", side_effect=_mock_sealion)
def test_golden_path_food_image(mock_expert_llm, mock_llm, mock_triage_llm):
    """Step 2 of golden path: food image → Expert skips diet question."""
    app = build_graph()

    # Simulate: user sends food image, Vision Agent returns result
    state = ChatState(
        user_input="我拍了一张食物照片",
        input_mode="text",
        chat_mode="personal",
        user_id="test_user",
        history=[],
        user_profile={"name": "测试用户", "language": "Chinese",
                      "conditions": ["Type 2 Diabetes"], "medications": ["Metformin"]},
        image_paths=None,
        vision_result=[{
            "scene_type": "FOOD",
            "items": [{"name": "海南鸡饭", "quantity": "1份",
                       "nutrition": {"calories_kcal": 600}}],
            "total_calories_kcal": 600,
            "confidence": 0.85,
        }],
        conversation_stage=None,
        collected_info=None,
    )

    result = app.invoke(state)

    # Expert should have pre-filled diet from vision_result
    collected = result.get("collected_info", {})
    assert collected.get("diet") is not None, "Diet should be pre-filled from vision"
    assert result.get("response") is not None


@patch("agents.triage.call_sealion", side_effect=_mock_sealion_single)
@patch("utils.llm_factory.call_sealion_with_history", side_effect=_mock_sealion)
@patch("agents.expert.call_sealion_with_history", side_effect=_mock_sealion)
def test_golden_path_all_confirmed_gives_summary(mock_expert_llm, mock_llm, mock_triage_llm):
    """When all fields are confirmed, Expert should give summary."""
    app = build_graph()

    state = ChatState(
        user_input="好的",
        input_mode="text",
        chat_mode="personal",
        user_id="test_user",
        history=[],
        user_profile={"name": "测试用户", "language": "Chinese",
                      "conditions": ["Type 2 Diabetes"], "medications": ["Metformin"]},
        image_paths=None,
        vision_result=[{
            "scene_type": "MEDICATION",
            "drug_name": "Metformin",
            "dosage": "500mg",
            "confidence": 0.9,
        }],
        conversation_stage="asking_glucose",
        collected_info={
            "glucose": {"value": "7.2 mmol/L", "confidence": None, "source": "user"},
            "diet": {"value": "海南鸡饭 (约600大卡)", "confidence": 0.85, "source": "vision"},
        },
    )

    result = app.invoke(state)

    collected = result.get("collected_info", {})
    assert collected.get("medication") is not None, "Medication should be filled from vision"
```

**Step 2: Run integration test**

```bash
python -m pytest tests/test_golden_path.py -v
```

**Step 3: Fix any issues found**

Iterate until tests pass.

**Step 4: Commit**

```bash
git add tests/test_golden_path.py
git commit -m "test: add golden path integration tests"
```

---

## Task 7: Manual Demo Validation

**Files:** None (manual testing)

**Step 1: Prepare test images**

Use existing test images from Vision Agent:
```bash
ls /Users/jamie/Documents/Python_Basic_Study/SG-INNOVATION/SG_INNOVATION/test_images/food/
```

**Step 2: Run the full demo golden path manually**

```bash
cd /Users/jamie/Documents/Python_Basic_Study/SG-INNOVATION/Health-Companion
python main.py

# Step 1: "你好"
# Step 2: "image /path/to/chicken_rice.jpg"
# Step 3: "最近空腹血糖 7.2"
# Step 4: "image /path/to/metformin.jpg"
# Step 5: "唉，我最近压力好大，管不住嘴"
```

**Step 3: Verify each step matches design expectations**

- Step 1: Chitchat agent responds
- Step 2: Vision recognizes food, Expert asks about glucose (skips diet)
- Step 3: Expert stores glucose, asks about medication
- Step 4: Vision recognizes medication, all confirmed, gives summary + alert_trigger
- Step 5: Companion agent responds with emotional support

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat: chatbot integration complete — golden path validated"
```
