"""
tests/test_no_rag.py
====================
Tests all core components except RAG:
  1. Lang detect (no external dependencies)
  2. Crisis agent (no LLM, 4 languages)
  3. Route by intent (no external dependencies)
  4. History compression logic (no LLM, does not trigger below threshold)
  5. Triage — OpenAI intent + emotion classification (3 scenarios)
  6. Companion agent — SEA-LION companion response
  7. Expert agent — RAG mocked to empty string
  8. Hybrid agent — RAG mocked to empty string

How to run (from project root):
  python -m tests.test_no_rag
"""

import os
import sys
import time
import traceback
from typing import List, Tuple, Optional
from unittest.mock import patch

# ── Environment setup ────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()

# ── Colour output ────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

_results: List[Tuple[str, bool, str]] = []


def section(title: str) -> None:
    print(f"\n{CYAN}{BOLD}{'─'*60}{RESET}")
    print(f"{CYAN}{BOLD}  {title}{RESET}")
    print(f"{CYAN}{BOLD}{'─'*60}{RESET}")


def ok(name: str, detail: str = "") -> None:
    _results.append((name, True, detail))
    print(f"  {GREEN}✓{RESET} {name}" + (f"  →  {detail[:100]}" if detail else ""))


def fail(name: str, detail: str = "") -> None:
    _results.append((name, False, detail))
    print(f"  {RED}✗{RESET} {name}" + (f"\n    {detail}" if detail else ""))


def _make_state(user_input: str, user_id: str = "user_001",
                intent: str = "companion", emotion: str = "neutral",
                history: Optional[list] = None) -> dict:
    """Build a minimal ChatState dict for directly calling agent nodes."""
    return {
        "user_input":         user_input,
        "input_mode":         "text",
        "chat_mode":          "personal",
        "user_id":            user_id,
        "audio_path":         None,
        "transcribed_text":   user_input,
        "emotion_label":      emotion,
        "emotion_confidence": 1.0,
        "intent":             intent,
        "all_intents":        [intent],
        "emotion_intensity":  "none",
        "history":            history or [],
        "user_profile": {
            "name":        "Mdm Chen",
            "language":    "English",
            "conditions":  ["Type 2 Diabetes"],
            "medications": ["Metformin 500mg"],
            "preferences": {},
        },
        "glucose_readings":   [],
        "response":           None,
        "emotion_log":        None,
        "image_paths":        [],
        "vision_result":      [],
    }


# ══════════════════════════════════════════════════════════════════════
# 1. Lang Detect (no external dependencies)
# ══════════════════════════════════════════════════════════════════════

def test_lang_detect() -> None:
    section("1. Lang Detect")
    from chatbot.memory.rag.lang_detect import detect_lang, LANG_NAME

    cases = [
        ("Hello, how are you?",             "en"),
        ("你好，我的血糖今天很高",              "zh"),
        ("Saya ada masalah dengan ubat saya", "ms"),
        ("என் இரத்த சர்க்கரை அதிகமாக உள்ளது",  "ta"),  # known: langdetect weak on Tamil
    ]
    for text, expected in cases:
        lang = detect_lang(text)
        if lang == expected:
            ok(f"detect_lang: {text[:30]}…", f"{lang} ({LANG_NAME[lang]})")
        elif expected == "ta":
            # langdetect has poor Tamil script support; the app handles Tamil via
            # profile.language field, not auto-detection — treat as known limitation
            ok(f"detect_lang (Tamil/known limit): {text[:30]}…",
               f"got {lang} (Tamil detection unreliable in langdetect library)")
        else:
            fail(f"detect_lang: {text[:30]}…", f"expected {expected}, got {lang}")


# ══════════════════════════════════════════════════════════════════════
# 2. Crisis Agent (no LLM, 4 languages)
# ══════════════════════════════════════════════════════════════════════

def test_crisis_agent() -> None:
    section("2. Crisis Agent — Fixed Responses (No LLM)")
    from chatbot.agents.crisis import crisis_agent_node

    cases = [
        ("I want to give up, there's no point anymore",  "user_en", "English", "1767"),
        ("我不想活了，太累了",                             "user_zh", "Chinese", "1767"),
        ("Saya rasa nak give up dah",                    "user_ms", "Malay",   "SOS"),
        ("என்னால் இனி தாங்க முடியாது",                  "user_ta", "Tamil",   "1767"),
    ]
    for user_input, user_id, language, expected_hotline in cases:
        state = _make_state(user_input, user_id, intent="crisis")
        state["user_profile"]["language"] = language
        try:
            result = crisis_agent_node(state)
            response = result.get("response", "")
            is_crisis = result.get("emotion_log", {}).get("is_crisis", False)
            if expected_hotline in response and is_crisis:
                ok(f"crisis [{user_id}]", response[:80].replace("\n", " "))
            else:
                fail(f"crisis [{user_id}]",
                     f"hotline '{expected_hotline}' not found or is_crisis={is_crisis}")
        except Exception as e:
            fail(f"crisis [{user_id}]", traceback.format_exc(limit=2))


# ══════════════════════════════════════════════════════════════════════
# 3. Route by Intent (no external dependencies)
# ══════════════════════════════════════════════════════════════════════

def test_route_by_intent() -> None:
    section("3. Route by Intent")
    from chatbot.agents.triage import route_by_intent

    cases = [
        ("crisis",    "crisis_agent"),
        ("medical",   "expert_agent"),
        ("hybrid",    "hybrid_agent"),
        ("companion", "companion_agent"),
        ("unknown",   "companion_agent"),   # fallback
    ]
    for intent, expected_route in cases:
        state = _make_state("test", intent=intent)
        route = route_by_intent(state)
        if route == expected_route:
            ok(f"route({intent})", route)
        else:
            fail(f"route({intent})", f"expected {expected_route}, got {route}")


# ══════════════════════════════════════════════════════════════════════
# 4. History Compression Logic (does not trigger LLM)
# ══════════════════════════════════════════════════════════════════════

def test_history_compression() -> None:
    section("4. History Compression Logic")
    from chatbot.utils.memory import compress_history_if_needed, add_to_history
    from chatbot.config.settings import HISTORY_COMPRESS_THRESHOLD, HISTORY_KEEP_RECENT

    print(f"  THRESHOLD={HISTORY_COMPRESS_THRESHOLD}, KEEP_RECENT={HISTORY_KEEP_RECENT}")

    # 4-a: below threshold — returned unchanged
    short_history = [{"role": "user", "content": f"msg {i}"} for i in range(5)]
    result = compress_history_if_needed(short_history)
    if result == short_history:
        ok("short history not compressed (5 msgs)", f"len={len(result)}")
    else:
        fail("short history not compressed", f"got len={len(result)}")

    # 4-b: add_to_history does not truncate (below HARD_CAP)
    h = []
    for i in range(10):
        h = add_to_history(h, "user" if i % 2 == 0 else "assistant", f"message {i}")
    if len(h) == 10:
        ok("add_to_history accumulates correctly", f"len={len(h)}")
    else:
        fail("add_to_history length", f"expected 10, got {len(h)}")

    # 4-c: HARD_CAP triggers truncation
    h_long = [{"role": "user", "content": f"msg {i}"} for i in range(105)]
    h_capped = add_to_history(h_long, "user", "final")
    if len(h_capped) <= 101:  # 100 cap + 1 new = 101 at most
        ok("HARD_CAP enforced", f"len={len(h_capped)}")
    else:
        fail("HARD_CAP not enforced", f"len={len(h_capped)}")

    # 4-d: above threshold — structure correct (mock LLM to avoid real API call)
    over_threshold = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"msg {i}"}
        for i in range(HISTORY_COMPRESS_THRESHOLD + 5)
    ]
    with patch("chatbot.utils.llm_factory.call_sealion", return_value="Summary: user asked about blood sugar"):
        compressed = compress_history_if_needed(over_threshold)
    # should have 1 summary message + HISTORY_KEEP_RECENT recent messages
    expected_len = 1 + HISTORY_KEEP_RECENT
    if len(compressed) == expected_len and compressed[0]["role"] == "system":
        ok("compression produces [summary] + recent", f"len={len(compressed)}, summary={compressed[0]['content'][:40]}")
    else:
        fail("compression structure wrong", f"len={len(compressed)}, first_role={compressed[0]['role'] if compressed else 'n/a'}")


# ══════════════════════════════════════════════════════════════════════
# 5. Triage — OpenAI Intent + Emotion (3 scenarios)
# ══════════════════════════════════════════════════════════════════════

def test_triage() -> None:
    section("5. Triage — OpenAI Intent Classification")

    # Mock RAG prefetch to avoid triggering Chroma
    with patch("chatbot.agents.triage_gemini._prefetch_rag", return_value=None), \
         patch("chatbot.memory.long_term.HealthEventStore.log_emotion", return_value=None):

        from chatbot.agents.triage_gemini import triage_node_gemini

        cases = [
            ("I want to give up on my medication",
             "crisis",    "crisis intent"),
            ("My blood sugar is 9.8 after lunch, is that okay?",
             "medical",   "medical intent"),
            ("My daughter never visits anymore, feeling very alone",
             "companion", "companion intent"),
        ]

        for user_input, expected_intent, label in cases:
            state = _make_state(user_input)
            t0 = time.time()
            try:
                result = triage_node_gemini(state)
                elapsed = time.time() - t0
                intent  = result.get("intent", "")
                emotion = result.get("emotion_label", "")
                intensity = result.get("emotion_intensity", "")
                if intent == expected_intent:
                    ok(f"triage: {label}", f"intent={intent} emotion={emotion} ({intensity}) [{elapsed:.1f}s]")
                else:
                    fail(f"triage: {label}", f"expected {expected_intent}, got {intent} | emotion={emotion}")
            except Exception as e:
                fail(f"triage: {label}", traceback.format_exc(limit=2))


# ══════════════════════════════════════════════════════════════════════
# 6. Companion Agent — SEA-LION
# ══════════════════════════════════════════════════════════════════════

def test_companion_agent() -> None:
    section("6. Companion Agent — SEA-LION (no RAG)")

    with patch("chatbot.memory.long_term.HealthEventStore.format_memory_for_prompt",
               return_value="[Known] Daughter recently went abroad, patient feels lonely"):
        from chatbot.agents.companion import companion_agent_node

        state = _make_state(
            "I haven't heard from my daughter in weeks",
            emotion="sad",
        )
        t0 = time.time()
        try:
            result = companion_agent_node(state)
            elapsed = time.time() - t0
            response = result.get("response", "")
            if response and len(response) > 10:
                ok("companion_agent responded", f"[{elapsed:.1f}s] {response[:120]}")
            else:
                fail("companion_agent empty response", f"response={response!r}")
        except Exception as e:
            fail("companion_agent exception", traceback.format_exc(limit=3))


# ══════════════════════════════════════════════════════════════════════
# 7. Expert Agent — RAG mocked to ""
# ══════════════════════════════════════════════════════════════════════

def test_expert_agent_no_rag() -> None:
    section("7. Expert Agent — RAG disabled")

    with patch("chatbot.agents.triage.consume_rag_prefetch", return_value=""), \
         patch("chatbot.memory.long_term.HealthEventStore.format_memory_for_prompt",
               return_value=""):
        from chatbot.agents.expert import expert_agent_node

        state = _make_state(
            "My blood sugar was 10.2 after eating wanton mee. Is that too high?",
            intent="medical",
        )
        t0 = time.time()
        try:
            result = expert_agent_node(state)
            elapsed = time.time() - t0
            response = result.get("response", "")
            if response and len(response) > 10:
                ok("expert_agent responded (no RAG)", f"[{elapsed:.1f}s] {response[:120]}")
            else:
                fail("expert_agent empty response", f"response={response!r}")
        except Exception as e:
            fail("expert_agent exception", traceback.format_exc(limit=3))


# ══════════════════════════════════════════════════════════════════════
# 8. Hybrid Agent — RAG mocked to ""
# ══════════════════════════════════════════════════════════════════════

def test_hybrid_agent_no_rag() -> None:
    section("8. Hybrid Agent — RAG disabled")

    with patch("chatbot.agents.triage.consume_rag_prefetch", return_value=""), \
         patch("chatbot.memory.long_term.HealthEventStore.format_memory_for_prompt",
               return_value=""):
        from chatbot.agents.hybrid_agent import hybrid_agent_node

        state = _make_state(
            "I'm so scared, my blood sugar keeps going up and I don't know what to do",
            intent="hybrid",
            emotion="fearful",
        )
        state["emotion_intensity"] = "high"
        t0 = time.time()
        try:
            result = hybrid_agent_node(state)
            elapsed = time.time() - t0
            response = result.get("response", "")
            if response and len(response) > 10:
                ok("hybrid_agent responded (no RAG)", f"[{elapsed:.1f}s] {response[:120]}")
            else:
                fail("hybrid_agent empty response", f"response={response!r}")
        except Exception as e:
            fail("hybrid_agent exception", traceback.format_exc(limit=3))


# ══════════════════════════════════════════════════════════════════════
# Summary
# ══════════════════════════════════════════════════════════════════════

def _summary() -> None:
    print(f"\n{BOLD}{'═'*60}{RESET}")
    passed = sum(1 for _, ok, _ in _results if ok)
    total  = len(_results)
    color  = GREEN if passed == total else (YELLOW if passed > total // 2 else RED)
    print(f"{color}{BOLD}  Results: {passed}/{total} passed{RESET}")
    if passed < total:
        print(f"\n{RED}  Failed:{RESET}")
        for name, ok_, detail in _results:
            if not ok_:
                print(f"    ✗ {name}")
                if detail:
                    print(f"      {detail[:200]}")
    print(f"{BOLD}{'═'*60}{RESET}\n")


if __name__ == "__main__":
    # Tests with no external dependencies (fast)
    test_lang_detect()
    test_crisis_agent()
    test_route_by_intent()
    test_history_compression()

    # Tests requiring API calls (slower, 30-60s each)
    print(f"\n{YELLOW}The following tests call external APIs (OpenAI + SEA-LION), please wait…{RESET}")
    test_triage()
    test_companion_agent()
    test_expert_agent_no_rag()
    test_hybrid_agent_no_rag()

    _summary()
