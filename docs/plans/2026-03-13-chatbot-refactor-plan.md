# Chatbot Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor chatbot to match PRD v0.3 — rename device_sync→glucose_reader, remove task intent/node, move crisis detection to triage, unify emotion logic (voice-only, 0.6 threshold), add daily_emotion_log table.

**Architecture:** Modify Bailey's existing LangGraph chatbot on `bailey-latest` branch. Changes are mostly subtractive (remove task_forward, alert_forward, health_events writes, emotion keywords) plus one addition (daily_emotion_log table + crisis detection in triage). Graph short-circuits on crisis detection.

**Tech Stack:** Python 3.11+, LangGraph, SQLite, pytest

---

## Task 1: Rename device_sync → glucose_reader (read-only, glucose only)

**Files:**
- Rename: `chatbot/agents/device_sync.py` → `chatbot/agents/glucose_reader.py`
- Modify: `chatbot/graph/builder.py`
- Modify: `chatbot/state/chat_state.py`
- Test: `chatbot/tests/test_glucose_reader.py`

**Step 1: Write the failing test**

Create `chatbot/tests/test_glucose_reader.py`:

```python
"""Test glucose_reader node."""
from chatbot.agents.glucose_reader import glucose_reader_node

_MOCK_CGM = [
    {"recorded_at": "2026-03-13T14:00:00", "glucose": 7.2},
    {"recorded_at": "2026-03-13T14:10:00", "glucose": 7.5},
    {"recorded_at": "2026-03-13T14:20:00", "glucose": 8.1},
]


def test_glucose_reader_returns_readings():
    state = {"user_id": "user_001"}
    result = glucose_reader_node(state)
    assert "glucose_readings" in result
    assert isinstance(result["glucose_readings"], list)


def test_glucose_reader_no_medication():
    """glucose_reader should NOT return medication data."""
    state = {"user_id": "user_001"}
    result = glucose_reader_node(state)
    assert "device_data" not in result
    assert "medication" not in result.get("glucose_readings", [{}])[0] if result.get("glucose_readings") else True
```

**Step 2: Run test to verify it fails**

Run: `cd chatbot && python -m pytest tests/test_glucose_reader.py -v`
Expected: FAIL (module not found)

**Step 3: Create glucose_reader.py**

Create `chatbot/agents/glucose_reader.py`:

```python
"""
glucose_reader — 读取共享数据库最近 1 小时血糖（最多 6 条 raw value）
生产环境：替换 _MOCK_CGM_DATA 为真实数据库查询
"""
from chatbot.state.chat_state import ChatState

# ── Mock data（生产环境替换为 SELECT * FROM user_cgm_log WHERE ...）──
_MOCK_CGM_DATA = {
    "user_001": [
        {"recorded_at": "2026-03-13T14:00:00", "glucose": 6.8},
        {"recorded_at": "2026-03-13T14:10:00", "glucose": 7.2},
        {"recorded_at": "2026-03-13T14:20:00", "glucose": 8.5},
    ],
    "user_002": [
        {"recorded_at": "2026-03-13T14:00:00", "glucose": 7.1},
        {"recorded_at": "2026-03-13T14:10:00", "glucose": 10.3},
    ],
}


def glucose_reader_node(state: ChatState) -> dict:
    """读取最近 1 小时血糖数据（最多 6 条），注入 state。只读，不写。"""
    user_id = state["user_id"]
    readings = _MOCK_CGM_DATA.get(user_id, [])
    # 最多 6 条
    readings = readings[-6:]
    print(f"[GlucoseReader] {len(readings)} 条血糖数据")
    return {"glucose_readings": readings}
```

**Step 4: Update ChatState** — replace `device_data` with `glucose_readings`

In `chatbot/state/chat_state.py`, replace:
```python
    device_data:        Optional[dict]   # {"glucose": [...], "medication": {...}}
```
with:
```python
    glucose_readings:   Optional[list]   # [{recorded_at, glucose}, ...] 最近1小时
```

Also remove `task_trigger` field:
```python
    task_trigger:       Optional[dict]    # DELETE THIS LINE
```

**Step 5: Update builder.py** — swap device_sync for glucose_reader

In `chatbot/graph/builder.py`:
- Replace import: `from chatbot.agents.device_sync import device_sync_node` → `from chatbot.agents.glucose_reader import glucose_reader_node`
- Replace node registration: `graph.add_node("device_sync", device_sync_node)` → `graph.add_node("glucose_reader", glucose_reader_node)`
- Replace edge: `graph.add_edge("input_node", "device_sync")` → `graph.add_edge("input_node", "glucose_reader")`
- Replace edge: `graph.add_edge("device_sync", "triage_node")` → `graph.add_edge("glucose_reader", "triage_node")`

**Step 6: Run test to verify it passes**

Run: `cd chatbot && python -m pytest tests/test_glucose_reader.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add chatbot/agents/glucose_reader.py chatbot/tests/test_glucose_reader.py chatbot/state/chat_state.py chatbot/graph/builder.py
git commit -m "refactor: rename device_sync to glucose_reader, read-only glucose"
```

---

## Task 2: Remove task_forward node + task intent

**Files:**
- Delete: `chatbot/agents/task_forward.py`
- Modify: `chatbot/graph/builder.py`
- Modify: `chatbot/agents/triage.py` (remove task keywords + task from route_map)
- Modify: `chatbot/config/settings.py` (remove INTENT_TASK)
- Modify: `chatbot/agents/expert.py` (remove task_trigger logic)
- Test: `chatbot/tests/test_triage.py`

**Step 1: Update settings.py**

In `chatbot/config/settings.py`:
- Remove `INTENT_TASK = "task"` line
- Remove `INTENT_ALERT = "alert"` line
- Remove `INTENT_TASK` and `INTENT_ALERT` from `ALL_INTENTS` list

**Step 2: Update triage.py**

In `chatbot/agents/triage.py`:
- Remove task keywords from `KEYWORD_RULES`: delete the `("task", [...])` entry
- Remove `"task"` from `route_by_intent` route_map
- Remove `"task"` from LLM system_prompt intent labels
- Update `route_by_intent` to not include task_forward

**Step 3: Update builder.py**

In `chatbot/graph/builder.py`:
- Remove import: `from chatbot.agents.task_forward import task_forward_node`
- Remove node: `graph.add_node("task_forward", task_forward_node)`
- Remove from conditional_edges map: `"task_forward": "task_forward"`
- Remove from history_update edge loop: `"task_forward"`

**Step 4: Update expert.py**

In `chatbot/agents/expert.py`:
- Remove the entire task_trigger/task_suffix block (lines 91-100)
- Remove `task_trigger` from return dict
- Remove `task_suffix` from system_prompt

**Step 5: Update test_triage.py**

In `chatbot/tests/test_triage.py`:
- Delete `test_task_keywords` test
- Delete `test_alert_keywords` test (alert intent also removed)

**Step 6: Run tests**

Run: `cd chatbot && python -m pytest tests/test_triage.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git rm chatbot/agents/task_forward.py
git add chatbot/config/settings.py chatbot/agents/triage.py chatbot/graph/builder.py chatbot/agents/expert.py chatbot/tests/test_triage.py
git commit -m "refactor: remove task_forward node and task intent"
```

---

## Task 3: Unify emotion logic (voice-only, 0.6 threshold)

**Files:**
- Modify: `chatbot/agents/triage.py` (remove EMOTION_KEYWORDS, simplify _simple_emotion_detect, update latest_emotion threshold)
- Modify: `chatbot/memory/long_term.py` (update upsert_emotion_log docstring)
- Test: `chatbot/tests/test_triage.py`

**Step 1: Update test_triage.py first**

Replace emotion-related tests in `chatbot/tests/test_triage.py`:

```python
# DELETE these tests:
# test_simple_emotion_detects_sad
# test_simple_emotion_detects_anxious
# test_simple_emotion_defaults_neutral
# test_simple_emotion_uses_voice_when_confident

# ADD these tests:
def test_emotion_voice_confident_uses_meralion():
    """Voice + confidence >= 0.6 should use MERaLiON result."""
    from chatbot.agents.triage import resolve_emotion
    assert resolve_emotion("sad", 0.8, "voice") == "sad"
    assert resolve_emotion("anxious", 0.6, "voice") == "anxious"

def test_emotion_voice_low_confidence_neutral():
    """Voice + confidence < 0.6 should be neutral."""
    from chatbot.agents.triage import resolve_emotion
    assert resolve_emotion("sad", 0.5, "voice") == "neutral"
    assert resolve_emotion("angry", 0.3, "voice") == "neutral"

def test_emotion_text_always_neutral():
    """Text input should always be neutral regardless of content."""
    from chatbot.agents.triage import resolve_emotion
    assert resolve_emotion("neutral", 0.0, "text") == "neutral"
    assert resolve_emotion("sad", 0.9, "text") == "neutral"  # text mode ignores voice data
```

**Step 2: Run tests to verify they fail**

Run: `cd chatbot && python -m pytest tests/test_triage.py -v`
Expected: FAIL (resolve_emotion not found)

**Step 3: Update triage.py**

In `chatbot/agents/triage.py`:

Delete `EMOTION_KEYWORDS` dict entirely.

Replace `_simple_emotion_detect` with:

```python
def resolve_emotion(
    voice_emotion: str,
    voice_confidence: float,
    input_mode: str,
) -> str:
    """Unified emotion resolution: voice >= 0.6 → use result, otherwise neutral."""
    if input_mode == "voice" and voice_confidence >= 0.6:
        return voice_emotion
    return "neutral"
```

Update all calls from `_simple_emotion_detect(user_input, emotion_label, emotion_confidence, input_mode)` to `resolve_emotion(emotion_label, emotion_confidence, input_mode)`.

Update `input_node` voice section — change threshold from 0.5 to 0.6:
```python
        if result["emotion_confidence"] >= 0.6:
            get_health_store().upsert_emotion_log(
                state["user_id"], result["emotion_label"]
            )
```

**Step 4: Run tests**

Run: `cd chatbot && python -m pytest tests/test_triage.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add chatbot/agents/triage.py chatbot/tests/test_triage.py
git commit -m "refactor: unify emotion to voice-only with 0.6 threshold"
```

---

## Task 4: Move crisis detection to triage (graph short-circuit)

**Files:**
- Modify: `chatbot/agents/triage.py` (add crisis patterns + detection)
- Modify: `chatbot/agents/companion.py` (remove crisis detection)
- Modify: `chatbot/graph/builder.py` (add conditional edge from triage for crisis short-circuit)
- Delete: `chatbot/agents/alert_forward.py`
- Test: `chatbot/tests/test_triage.py`
- Test: `chatbot/tests/test_crisis.py` (new)

**Step 1: Write failing test**

Create `chatbot/tests/test_crisis.py`:

```python
"""Test crisis detection in triage layer."""
from chatbot.agents.triage import is_crisis


def test_crisis_chinese_patterns():
    assert is_crisis("我不想活了")
    assert is_crisis("活着没什么意思")
    assert is_crisis("我想伤害自己")


def test_crisis_english_patterns():
    assert is_crisis("I want to die")
    assert is_crisis("no point living anymore")


def test_non_crisis_not_triggered():
    assert not is_crisis("我今天很难过")
    assert not is_crisis("血糖高了怎么办")
    assert not is_crisis("打卡")
```

**Step 2: Run test to verify it fails**

Run: `cd chatbot && python -m pytest tests/test_crisis.py -v`
Expected: FAIL (is_crisis not found in triage)

**Step 3: Move crisis detection to triage.py**

Move from `companion.py` to `triage.py`:

```python
import re

_CRISIS_PATTERNS = [
    r"活着.*没.*意思", r"不想.*活", r"去死", r"伤害.*自己", r"结束.*生命",
    r"no\s*point\s*living", r"want\s*to\s*die", r"hurt\s*myself", r"end\s*my\s*life",
]

def is_crisis(text: str) -> bool:
    """Check for suicide/self-harm crisis keywords."""
    return any(re.search(p, text) for p in _CRISIS_PATTERNS)
```

Add crisis response function to triage.py:

```python
def _crisis_response(state: ChatState) -> dict:
    """Generate crisis response + alert_trigger. Called when triage detects crisis."""
    profile = state.get("user_profile", {})
    name = profile.get("name", "您")
    language = profile.get("language", "Chinese")
    user_id = state["user_id"]
    user_input = state["user_input"]

    response = (
        f"{name}，您刚才说的话让我很担心。"
        "您的生命很重要，您不需要一个人扛着这些。"
        "请拨打新加坡心理援助热线：1-767（24小时）或 IMH：6389 2222。"
        "我在这里陪您——能告诉我，是什么让您有这样的感受吗？"
    ) if language != "English" else (
        "I'm really concerned about what you said. You matter and you're not alone. "
        "Please call Samaritans of Singapore: 1-767 (24hr) or IMH: 6389 2222."
    )

    from datetime import datetime
    return {
        "response": response,
        "intent": "crisis",
        "alert_trigger": {
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "alert_input": user_input,
            "severity": "心理危机",
        },
    }
```

Update `triage_node` to check crisis FIRST:

```python
def triage_node(state: ChatState) -> dict:
    user_input = state["user_input"]
    # Crisis check first — short-circuits entire pipeline
    if is_crisis(user_input):
        print(f"[Triage] ⚠️ 心理危机检测触发")
        return _crisis_response(state)
    return _full_triage(state)
```

**Step 4: Update graph builder for crisis short-circuit**

In `chatbot/graph/builder.py`:

Replace the fixed edge `triage_node → policy_node` with a conditional edge:

```python
def _route_after_triage(state: ChatState) -> str:
    """Crisis → skip to history_update; normal → continue to policy."""
    if state.get("intent") == "crisis":
        return "history_update"
    return "policy_node"

# Replace: graph.add_edge("triage_node", "policy_node")
# With:
graph.add_conditional_edges(
    "triage_node",
    _route_after_triage,
    {
        "history_update": "history_update",
        "policy_node": "policy_node",
    }
)
```

**Step 5: Remove crisis detection from companion.py**

In `chatbot/agents/companion.py`:
- Delete `_CRISIS_PATTERNS` list
- Delete `_is_crisis` function
- Delete the entire `if _is_crisis(user_input):` block from `companion_agent_node`
- Remove `import re` if no longer needed

**Step 6: Delete alert_forward.py**

```bash
git rm chatbot/agents/alert_forward.py
```

**Step 7: Run all tests**

Run: `cd chatbot && python -m pytest tests/test_crisis.py tests/test_triage.py -v`
Expected: PASS

**Step 8: Commit**

```bash
git rm chatbot/agents/alert_forward.py
git add chatbot/agents/triage.py chatbot/agents/companion.py chatbot/graph/builder.py chatbot/tests/test_crisis.py
git commit -m "feat: move crisis detection to triage with graph short-circuit"
```

---

## Task 5: Add daily_emotion_log table + write logic

**Files:**
- Modify: `chatbot/memory/long_term.py` (add daily_emotion_log table + methods)
- Modify: `chatbot/agents/triage.py` (write to daily_emotion_log after emotion resolution)
- Test: `chatbot/tests/test_emotion_storage.py` (new)

**Step 1: Write failing test**

Create `chatbot/tests/test_emotion_storage.py`:

```python
"""Test emotion storage: daily_emotion_log table."""
import os
import sqlite3
import tempfile
from unittest.mock import patch
from chatbot.memory.long_term import HealthEventStore


def test_log_daily_emotion():
    """Non-neutral emotion should be logged."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        with patch("chatbot.memory.long_term.DB_PATH", db_path):
            store = HealthEventStore()
            store.log_daily_emotion("user_001", "sad", "我今天很难过")
            logs = store.get_daily_emotions("user_001")
            assert len(logs) == 1
            assert logs[0]["emotion_label"] == "sad"
            assert logs[0]["user_input"] == "我今天很难过"
    finally:
        os.unlink(db_path)


def test_neutral_not_logged():
    """Neutral emotion should NOT be logged (caller responsibility, but verify method works)."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        with patch("chatbot.memory.long_term.DB_PATH", db_path):
            store = HealthEventStore()
            # Caller should not call this with neutral, but if they do it still stores
            store.log_daily_emotion("user_001", "neutral", "hello")
            logs = store.get_daily_emotions("user_001")
            assert len(logs) == 1  # method itself doesn't filter
    finally:
        os.unlink(db_path)


def test_clear_daily_emotions():
    """Clear daily emotions for a user."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        with patch("chatbot.memory.long_term.DB_PATH", db_path):
            store = HealthEventStore()
            store.log_daily_emotion("user_001", "sad", "难过")
            store.log_daily_emotion("user_001", "anxious", "焦虑")
            store.clear_daily_emotions("user_001")
            logs = store.get_daily_emotions("user_001")
            assert len(logs) == 0
    finally:
        os.unlink(db_path)
```

**Step 2: Run test to verify it fails**

Run: `cd chatbot && python -m pytest tests/test_emotion_storage.py -v`
Expected: FAIL (log_daily_emotion not found)

**Step 3: Add daily_emotion_log to long_term.py**

In `chatbot/memory/long_term.py`, add to `_init_db`:

```python
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_emotion_log (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id       TEXT NOT NULL,
                    emotion_label TEXT NOT NULL,
                    user_input    TEXT NOT NULL,
                    timestamp     TEXT NOT NULL
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_daily_emotion_user "
                "ON daily_emotion_log(user_id, timestamp)"
            )
```

Add methods to `HealthEventStore`:

```python
    def log_daily_emotion(self, user_id: str, emotion_label: str, user_input: str) -> None:
        """Log a non-neutral emotion + input for daily summary."""
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.execute(
                "INSERT INTO daily_emotion_log "
                "(user_id, emotion_label, user_input, timestamp) VALUES (?, ?, ?, ?)",
                (user_id, emotion_label, user_input, datetime.now().isoformat()),
            )

    def get_daily_emotions(self, user_id: str) -> list:
        """Get today's emotion log entries."""
        today = datetime.now().strftime("%Y-%m-%d")
        with sqlite3.connect(str(DB_PATH)) as conn:
            rows = conn.execute(
                "SELECT emotion_label, user_input, timestamp FROM daily_emotion_log "
                "WHERE user_id=? AND timestamp LIKE ? ORDER BY timestamp",
                (user_id, f"{today}%"),
            ).fetchall()
        return [
            {"emotion_label": r[0], "user_input": r[1], "timestamp": r[2]}
            for r in rows
        ]

    def clear_daily_emotions(self, user_id: str) -> None:
        """Clear today's emotion log (called after 23:59 summary)."""
        today = datetime.now().strftime("%Y-%m-%d")
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.execute(
                "DELETE FROM daily_emotion_log WHERE user_id=? AND timestamp LIKE ?",
                (user_id, f"{today}%"),
            )
```

**Step 4: Wire into triage — write daily_emotion_log after emotion resolution**

In `chatbot/agents/triage.py`, update both keyword path and LLM path in `_full_triage`:

After emotion is resolved, add:
```python
    if emotion != "neutral":
        get_health_store().log_daily_emotion(state["user_id"], emotion, user_input)
```

**Step 5: Run tests**

Run: `cd chatbot && python -m pytest tests/test_emotion_storage.py tests/test_triage.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add chatbot/memory/long_term.py chatbot/agents/triage.py chatbot/tests/test_emotion_storage.py
git commit -m "feat: add daily_emotion_log table with write logic in triage"
```

---

## Task 6: Update expert.py for new data sources

**Files:**
- Modify: `chatbot/agents/expert.py` (use glucose_readings instead of device_data, remove medication formatting, update diet formatting for flat FoodOutput)

**Step 1: Update expert.py**

Key changes:
- Replace `device_data.get("glucose", [])` → `state.get("glucose_readings", [])`
- Delete `_fmt_medication` function entirely
- Update `_fmt_glucose` to use new field names (`recorded_at` + `glucose` instead of `time` + `value`)
- Update `_fmt_diet` for flat FoodOutput schema: `vr.get("food_name")` instead of `vr.get("items", [])`
- Remove `med_str` from system_prompt
- Remove task_trigger from return dict (already done in Task 2, verify)

Updated `_fmt_glucose`:
```python
def _fmt_glucose(readings: list) -> str:
    if not readings:
        return "暂无近1小时数据"
    return "、".join(
        f"{r.get('recorded_at', '?')[-8:-3]} {r.get('glucose', '?')} mmol/L"
        for r in readings
    )
```

Updated `_fmt_diet`:
```python
def _fmt_diet(vision_result: list) -> str:
    if not vision_result:
        return ""
    foods = []
    for vr in vision_result:
        if vr.get("scene_type") == "FOOD" and not vr.get("error"):
            name = vr.get("food_name", "")
            cal = vr.get("total_calories", "")
            desc = name
            if cal:
                desc += f"（约{cal}大卡）"
            if desc:
                foods.append(desc)
    return "；".join(foods)
```

**Step 2: Run existing tests**

Run: `cd chatbot && python -m pytest -v`
Expected: PASS (or identify remaining failures)

**Step 3: Commit**

```bash
git add chatbot/agents/expert.py
git commit -m "refactor: update expert to use glucose_readings and flat FoodOutput"
```

---

## Task 7: Clean up companion.py (remove emotion_summary write)

**Files:**
- Modify: `chatbot/agents/companion.py` (remove per-conversation emotion_summary generation — will be replaced by 23:59 daily job later)

**Step 1: Update companion.py**

- Delete `_generate_emotion_summary` function
- Delete the entire "写入情绪摘要" block (lines 98-113)
- Keep: reading emotion_summary for context (line 79: `store.format_emotion_summary_for_llm`)
- Keep: emotion_log output in return dict
- Remove `call_sealion` from imports (only `call_sealion_with_history_stream` and `format_history_for_sealion` needed)

**Step 2: Run tests**

Run: `cd chatbot && python -m pytest -v`
Expected: PASS

**Step 3: Commit**

```bash
git add chatbot/agents/companion.py
git commit -m "refactor: remove per-conversation emotion_summary from companion (will be daily job)"
```

---

## Task 8: Clean up long_term.py (remove health_events writes)

**Files:**
- Modify: `chatbot/memory/long_term.py` (remove health_events table creation and related methods — chatbot no longer writes health events, only emotion tables)

**Step 1: Update long_term.py**

Keep:
- `emotion_log` table (latest_emotion) + `upsert_emotion_log` — update docstring to say "confidence >= 0.6"
- `daily_emotion_log` table + methods (added in Task 5)
- `get_emotion_summaries` + `format_emotion_summary_for_llm` — keep for reading (companion/expert still reads)
- `emotion_summary` read methods

Remove:
- `health_events` table creation from `_init_db` (or keep for backward compat, mark deprecated)
- `log_event` method (no longer used by chatbot — device_sync was the only writer)
- `get_recent` method
- `format_for_llm` method (was used by expert, now expert reads shared DB directly)

Note: `get_emotion_summaries` still reads from `health_events` table where `event_type='emotion_summary'`. This needs to be migrated to a dedicated `emotion_summary` table eventually, but for now keep reading from health_events (existing data).

**Step 2: Run tests**

Run: `cd chatbot && python -m pytest -v`
Expected: PASS

**Step 3: Commit**

```bash
git add chatbot/memory/long_term.py
git commit -m "refactor: remove health_events writes, chatbot only writes emotion tables"
```

---

## Task 9: Update golden_path tests

**Files:**
- Modify: `chatbot/tests/test_golden_path.py` (remove multi-turn conversation_stage tests, update to match single-turn expert + new state fields)

**Step 1: Rewrite golden_path tests**

The existing tests reference `conversation_stage`, `collected_info`, `task_forward` — all removed. Replace with tests that match the new architecture:

- `test_step1_chitchat` — keep, minor updates
- `test_step2_food_vision_prefills_diet` — rewrite: food photo → expert gives advice (no conversation_stage)
- `test_step3_glucose_collected` — delete (no conversation_stage)
- `test_step4_all_confirmed_gives_summary_and_alert` — delete (no conversation_stage)
- `test_step5_emotional_routes_to_companion` — keep
- Add: `test_crisis_short_circuits` — crisis input skips to history_update

Update `_build_state` to remove `conversation_stage`, `collected_info`, add `glucose_readings`.

**Step 2: Run tests**

Run: `cd chatbot && python -m pytest tests/test_golden_path.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add chatbot/tests/test_golden_path.py
git commit -m "test: update golden_path tests for single-turn expert + crisis short-circuit"
```

---

## Task 10: Delete device_sync.py + final cleanup

**Files:**
- Delete: `chatbot/agents/device_sync.py`
- Verify: no remaining imports of deleted modules

**Step 1: Delete old file**

```bash
git rm chatbot/agents/device_sync.py
```

**Step 2: Grep for stale references**

```bash
grep -r "device_sync" chatbot/ --include="*.py"
grep -r "task_forward" chatbot/ --include="*.py"
grep -r "alert_forward" chatbot/ --include="*.py"
grep -r "device_data" chatbot/ --include="*.py"
```

Fix any remaining references.

**Step 3: Run full test suite**

Run: `cd chatbot && python -m pytest -v`
Expected: ALL PASS

**Step 4: Commit**

```bash
git rm chatbot/agents/device_sync.py
git add -u
git commit -m "chore: delete device_sync.py and clean stale references"
```

---

## Summary of changes

| Action | File |
|--------|------|
| CREATE | `chatbot/agents/glucose_reader.py` |
| CREATE | `chatbot/tests/test_glucose_reader.py` |
| CREATE | `chatbot/tests/test_crisis.py` |
| CREATE | `chatbot/tests/test_emotion_storage.py` |
| DELETE | `chatbot/agents/device_sync.py` |
| DELETE | `chatbot/agents/task_forward.py` |
| DELETE | `chatbot/agents/alert_forward.py` |
| MODIFY | `chatbot/state/chat_state.py` |
| MODIFY | `chatbot/graph/builder.py` |
| MODIFY | `chatbot/agents/triage.py` |
| MODIFY | `chatbot/agents/expert.py` |
| MODIFY | `chatbot/agents/companion.py` |
| MODIFY | `chatbot/agents/policy.py` (minor) |
| MODIFY | `chatbot/config/settings.py` |
| MODIFY | `chatbot/memory/long_term.py` |
| MODIFY | `chatbot/tests/test_triage.py` |
| MODIFY | `chatbot/tests/test_golden_path.py` |
| CREATE | `chatbot/jobs/__init__.py` |
| CREATE | `chatbot/jobs/daily_summary.py` |
| CREATE | `chatbot/tests/test_daily_summary.py` |

---

## 待做：FastAPI 接入定时任务

**状态：逻辑已完成，未接入调度**

`chatbot/jobs/daily_summary.py` 中的 `run_daily_summary()` 已实现完整流程：
- 读 daily_emotion_log → 调 LLM 汇总 → 写 emotion_summary 表 → 清空当日 log
- 4 个测试全部通过

**待做：** 在 FastAPI lifespan 中用 APScheduler 注册 23:59 定时调度：

```python
# chatbot/api/main.py（示意）
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_daily_summary, "cron", hour=23, minute=59)
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)
```

**依赖：** 需要 `pip install apscheduler` 并加入 requirements.txt
