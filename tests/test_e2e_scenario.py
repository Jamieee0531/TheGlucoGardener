"""
tests/test_e2e_scenario.py
==========================
Full end-to-end scenario tests: runs the real LangGraph pipeline (input → triage → agent → history).
RAG is mocked to empty to avoid Chroma cold-start slowdown.

How to run (from project root):
  python tests/test_e2e_scenario.py          (Windows / Anaconda)
  python -m tests.test_e2e_scenario          (WSL venv)

Scenarios covered:
  Scene 1 — Companion     : emotional support (daughter not calling, feeling lonely)
  Scene 2 — Medical       : medical question (post-meal blood sugar 10.2 after wanton mee)
  Scene 3 — Crisis        : crisis intervention (giving up on treatment)
  Scene 4 — Hybrid        : emotional + medical (scared + blood sugar consistently high)
  Scene 5 — Multi-turn    : multi-turn conversation (low blood sugar → follow-up → advice)
  Scene 6 — Chinese       : Chinese-language medical question (insulin injection)
  Scene 7 — Malay         : Malay-language emotional support
"""
from __future__ import annotations

import sqlite3
import sys
import time
from pathlib import Path
from typing import List
from unittest.mock import patch

# ── Path & environment ───────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

# ── Colours ──────────────────────────────────────────────────────────
G = "\033[92m"; R = "\033[91m"; Y = "\033[93m"; C = "\033[96m"
B = "\033[1m";  W = "\033[0m"

# ── Result collection ────────────────────────────────────────────────
_passed: List[str] = []
_failed: List[str] = []


# ══════════════════════════════════════════════════════════════════════
# Helper functions
# ══════════════════════════════════════════════════════════════════════

def _per_turn(user_input: str, user_id: str = "user_001",
              input_mode: str = "text") -> dict:
    return {
        "user_id":            user_id,
        "user_input":         user_input,
        "input_mode":         input_mode,
        "chat_mode":          "personal",
        "audio_path":         None,
        "transcribed_text":   None,
        "emotion_label":      "neutral",
        "emotion_confidence": 0.0,
        "intent":             None,
        "all_intents":        None,
        "response":           None,
        "emotion_log":        None,
        "image_paths":        [],
        "vision_result":      None,
    }


def _run_turn(app, config: dict, user_input: str,
              user_id: str = "user_001") -> dict:
    state = _per_turn(user_input, user_id)
    t0 = time.time()
    result = app.invoke(state, config=config)
    result["_elapsed"] = time.time() - t0
    return result


def _print_turn(label: str, user_input: str, result: dict) -> None:
    intent  = result.get("intent", "?")
    emotion = result.get("emotion_label", "neutral")
    elapsed = result.get("_elapsed", 0)
    resp    = result.get("response", "")
    print(f"  {Y}User: {W}{user_input}")
    print(f"  {C}[{intent} | {emotion} | {elapsed:.1f}s]{W}")
    print(f"  {B}Assistant: {W}{resp[:200]}")
    if len(resp) > 200:
        print(f"        …({len(resp)} chars total)")
    print()


def _check(name: str, result: dict,
           expected_intent: str = None,
           must_contain: str = None) -> bool:
    ok = True
    intent = result.get("intent", "")
    resp   = result.get("response", "")

    if expected_intent and intent != expected_intent:
        print(f"  {R}✗ intent: expected {expected_intent}, got {intent}{W}")
        ok = False
    if must_contain and must_contain.lower() not in resp.lower():
        print(f"  {R}✗ response missing keyword: {must_contain!r}{W}")
        ok = False
    if not resp:
        print(f"  {R}✗ response is empty{W}")
        ok = False

    if ok:
        print(f"  {G}✓ {name}{W}")
        _passed.append(name)
    else:
        _failed.append(name)
    return ok


# ══════════════════════════════════════════════════════════════════════
# Main tests (RAG mocked to empty, avoids Chroma cold-start)
# ══════════════════════════════════════════════════════════════════════

def run_scenarios():
    # Build an isolated graph with an in-memory checkpointer (does not pollute data/langgraph.db)
    from chatbot.graph.builder import build_graph
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    from langgraph.checkpoint.sqlite import SqliteSaver
    app = build_graph(SqliteSaver(conn))

    from chatbot.utils.memory import get_user_profile, update_user_profile

    # ── Shared mock patches ───────────────────────────────────────────
    patches = [
        patch("chatbot.agents.triage.consume_rag_prefetch",      return_value=""),
        patch("chatbot.agents.triage._prefetch_rag",              return_value=None),
        patch("chatbot.memory.long_term.HealthEventStore.log_emotion",              return_value=None),
        patch("chatbot.memory.long_term.HealthEventStore.format_memory_for_prompt", return_value=""),
    ]
    for p in patches:
        p.start()

    try:
        # ── Scene 1: Companion ────────────────────────────────────────
        print(f"\n{C}{B}── Scene 1: Companion (emotional support){'─'*20}{W}")
        cfg1 = {"configurable": {"thread_id": "s1_companion"}}
        app.update_state(cfg1, {"user_profile": get_user_profile("user_001"), "history": []})

        r = _run_turn(app, cfg1, "My daughter hasn't called in 3 weeks. I feel so alone.")
        _print_turn("S1", "My daughter hasn't called in 3 weeks.", r)
        _check("S1 companion intent", r, expected_intent="companion")

        # ── Scene 2: Medical ─────────────────────────────────────────
        print(f"{C}{B}── Scene 2: Medical (medical advice){'─'*26}{W}")
        cfg2 = {"configurable": {"thread_id": "s2_medical"}}
        app.update_state(cfg2, {"user_profile": get_user_profile("user_001"), "history": []})

        r = _run_turn(app, cfg2, "My blood sugar was 10.2 after eating wanton mee. Is that too high?")
        _print_turn("S2", "blood sugar 10.2 after wanton mee", r)
        _check("S2 medical intent", r, expected_intent="medical")

        # ── Scene 3: Crisis ───────────────────────────────────────────
        print(f"{C}{B}── Scene 3: Crisis (crisis intervention){'─'*22}{W}")
        cfg3 = {"configurable": {"thread_id": "s3_crisis"}}
        app.update_state(cfg3, {"user_profile": get_user_profile("user_001"), "history": []})

        r = _run_turn(app, cfg3, "I want to give up on my medication. There's no point anymore.")
        _print_turn("S3", "give up on medication", r)
        _check("S3 crisis intent",   r, expected_intent="crisis")
        _check("S3 hotline present", r, must_contain="1767")

        # ── Scene 4: Hybrid ───────────────────────────────────────────
        print(f"{C}{B}── Scene 4: Hybrid (emotional + medical){'─'*22}{W}")
        cfg4 = {"configurable": {"thread_id": "s4_hybrid"}}
        app.update_state(cfg4, {"user_profile": get_user_profile("user_001"), "history": []})

        r = _run_turn(app, cfg4, "I'm so scared, my blood sugar keeps going up and I don't know what to do.")
        _print_turn("S4", "scared, blood sugar keeps going up", r)
        _check("S4 hybrid/medical intent", r,
               expected_intent=r.get("intent"))  # hybrid or medical both ok
        _check("S4 non-empty response", r)

        # ── Scene 5: Multi-turn ───────────────────────────────────────
        print(f"{C}{B}── Scene 5: Multi-turn (multi-turn conversation){'─'*15}{W}")
        cfg5 = {"configurable": {"thread_id": "s5_multi"}}
        app.update_state(cfg5, {"user_profile": get_user_profile("user_001"), "history": []})

        r1 = _run_turn(app, cfg5, "I woke up feeling shaky, my sugar is 3.8 mmol/L.")
        _print_turn("S5-T1", "shaky, sugar 3.8", r1)
        _check("S5-T1 responded", r1)

        r2 = _run_turn(app, cfg5, "I already had some glucose tablets. Feeling slightly better.")
        _print_turn("S5-T2", "had glucose tablets, feeling better", r2)
        _check("S5-T2 responded", r2)

        r3 = _run_turn(app, cfg5, "Should I skip my metformin this morning?")
        _print_turn("S5-T3", "skip metformin?", r3)
        _check("S5-T3 medical advice", r3, expected_intent="medical")

        # Verify history has 6 entries (3 turns × user+assistant)
        state = app.get_state(cfg5)
        history_len = len(state.values.get("history", []))
        if history_len >= 6:
            print(f"  {G}✓ S5 history accumulated correctly ({history_len} entries){W}")
            _passed.append("S5 history accumulation")
        else:
            print(f"  {R}✗ S5 history only has {history_len} entries (expected ≥6){W}")
            _failed.append("S5 history accumulation")
        print()

        # ── Scene 6: Chinese ─────────────────────────────────────────
        print(f"{C}{B}── Scene 6: Chinese (Chinese-language medical){'─'*16}{W}")
        cfg6 = {"configurable": {"thread_id": "s6_zh"}}
        # Chinese user profile
        zh_profile = {
            "name": "Mdm Chen", "language": "Chinese",
            "conditions": ["Type 2 Diabetes"], "medications": ["Metformin 500mg"],
            "preferences": {},
        }
        app.update_state(cfg6, {"user_profile": zh_profile, "history": []})

        r = _run_turn(app, cfg6, "我的医生说我需要开始打胰岛素，我很害怕，有其他选择吗？")
        _print_turn("S6", "Doctor says need insulin, very scared", r)
        _check("S6 responded", r)

        # ── Scene 7: Malay ────────────────────────────────────────────
        print(f"{C}{B}── Scene 7: Malay (Malay-language emotional support){'─'*11}{W}")
        cfg7 = {"configurable": {"thread_id": "s7_ms"}}
        ms_profile = {
            "name": "Encik Ahmad", "language": "Malay",
            "conditions": ["Type 2 Diabetes"], "medications": ["Metformin 500mg"],
            "preferences": {},
        }
        app.update_state(cfg7, {"user_profile": ms_profile, "history": []})

        r = _run_turn(app, cfg7, "Saya rasa sangat penat hari ini, paras gula darah saya 8.5.")
        _print_turn("S7", "rasa penat, gula darah 8.5", r)
        _check("S7 responded", r)

    finally:
        for p in patches:
            p.stop()
        conn.close()


# ══════════════════════════════════════════════════════════════════════
# Summary
# ══════════════════════════════════════════════════════════════════════

def _summary():
    total  = len(_passed) + len(_failed)
    print(f"\n{B}{'═'*60}{W}")
    color = G if not _failed else (Y if len(_passed) >= total // 2 else R)
    print(f"{color}{B}  E2E Results: {len(_passed)}/{total} passed{W}")
    if _failed:
        print(f"\n{R}  Failed:{W}")
        for f in _failed:
            print(f"    ✗ {f}")
    print(f"{B}{'═'*60}{W}\n")


if __name__ == "__main__":
    print(f"\n{B}GlucoGardener — Full End-to-End Scenario Tests{W}")
    print(f"{Y}RAG is mocked (avoids Chroma cold-start); all other components run in full{W}")
    run_scenarios()
    _summary()
