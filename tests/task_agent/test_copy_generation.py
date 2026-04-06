"""
Integration tests for SEA-LION copy generation pipeline.

These tests make real HTTP calls to the SEA-LION API.
Run them manually to verify the LLM pipeline end-to-end.

Run with:
    pytest tests/task_agent/test_copy_generation.py -v -s -m integration
"""
import pytest
from task_agent.agent.graph import copy_subgraph

# Minimal realistic state matching Auntie Lin's scenario
_BASE_STATE = {
    "user_id": "test",
    "trigger_source": "admin",
    "user_profile": {
        "name": "Auntie Lin",
        "bmi": 28.1,
        "language_pref": "en",
        "gender": "female",
        "weight_kg": 72.0,
        "height_cm": 160.0,
        "waist_cm": 89.0,
        "birth_year": 1974,
    },
    "calories_burned_today": 110.0,
    "avg_bg_last_2h": 5.6,
    "exercise_history": [
        {"type": "walking", "duration_min": 30, "calories_burned": 65.0},
        {"type": "walking", "duration_min": 40, "calories_burned": 80.0},
        {"type": "walking", "duration_min": 25, "calories_burned": 55.0},
    ],
    "last_gps": {"lat": 1.3526, "lng": 103.8352},
    "rule": {"base_calorie": 300, "trigger_threshold": 0.6, "exercise_pts": 50},
    "rule_result": {
        "should_trigger": True,
        "deficit_kcal": 220,
        "adjusted_target": 330,
        "low_bg_guard": False,
    },
    "selected_park": {
        "name": "Bishan-Ang Mo Kio Park",
        "lat": 1.3612,
        "lng": 103.8388,
        "distance_m": 1100,
    },
    "park_candidates": [],
}


@pytest.mark.asyncio
@pytest.mark.integration
async def test_writer_generates_real_copy():
    """
    Full LangGraph pipeline: analyst → advisor → writer → SEA-LION API.
    Verifies: no fallback, required fields present, body is non-trivial.
    """
    result = await copy_subgraph.ainvoke(_BASE_STATE)
    content = result.get("task_content", {})

    print(f"\n  title: {content.get('title')}")
    print(f"  body:  {content.get('body')}")
    print(f"  cta:   {content.get('cta')}")

    assert "_fallback_reason" not in content, (
        f"Writer fell back to template. Reason: {content.get('_fallback_reason')}"
    )
    assert "title" in content, "Missing 'title' key"
    assert "body" in content, "Missing 'body' key"
    assert "cta" in content, "Missing 'cta' key"
    assert len(content["body"]) > 20, "Body is too short — likely a bad LLM response"
    assert "Bishan" in content["body"] or "park" in content["body"].lower(), (
        "Park name not mentioned in body"
    )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_writer_low_bg_scenario():
    """
    When BG is low (3.8), advisor should recommend light intensity + snack.
    Writer should mention the snack in the copy.
    """
    state = {**_BASE_STATE, "avg_bg_last_2h": 3.8}
    result = await copy_subgraph.ainvoke(state)
    content = result.get("task_content", {})

    print(f"\n  body: {content.get('body')}")

    assert "_fallback_reason" not in content
    # Advisor sets snack = "15g fast carbs (e.g. banana slices)" when BG < 4.5
    # Writer should weave it in naturally
    body = content.get("body", "").lower()
    assert any(word in body for word in ["snack", "banana", "carb", "eat", "grab"]), (
        "Low BG scenario: expected snack mention in copy"
    )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_writer_chinese_output():
    """
    When language_pref is zh-CN, writer should respond in Chinese.
    """
    state = {
        **_BASE_STATE,
        "user_profile": {**_BASE_STATE["user_profile"], "language_pref": "zh-CN"},
    }
    result = await copy_subgraph.ainvoke(state)
    content = result.get("task_content", {})

    print(f"\n  title: {content.get('title')}")
    print(f"  body:  {content.get('body')}")

    assert "_fallback_reason" not in content
    body = content.get("body", "")
    # Check for Chinese characters
    assert any('\u4e00' <= c <= '\u9fff' for c in body), (
        "Expected Chinese characters in body when language_pref=zh-CN"
    )
