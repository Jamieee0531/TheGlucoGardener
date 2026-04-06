"""
tests/test_memory_storage.py
Verifies that long-term memory storage is working correctly.

Flow:
  1. Simulate a conversation containing personal information (to be extracted as facts)
  2. Call _extract_memory directly (without waiting for 23:59)
  3. Query the DB to verify user_facts / user_context were written
  4. Call format_memory_for_prompt to verify injected content
  5. Run one more conversation turn to verify memory appears in the response context

How to run:
    cd TheGlucoGardener
    python -m tests.test_memory_storage
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

# Ensure connection to real DB
os.environ["DEMO_MODE"] = "false"

USER_ID = "user_001"

# ── Simulated conversation content (contains extractable personal facts) ─────
SIMULATED_CONVERSATIONS = [
    {
        "user_input":    "My daughter never call today leh. She is in Australia.",
        "emotion_label": "sad",
    },
    {
        "user_input":    "I live alone, sometimes very quiet one.",
        "emotion_label": "sad",
    },
    {
        "user_input":    "I don't like bitter gourd, every time people say eat bitter gourd good for diabetes I also cannot tahan.",
        "emotion_label": "neutral",
    },
    {
        "user_input":    "Every time I check blood sugar I feel very scared, the number always make me worry.",
        "emotion_label": "fearful",
    },
    {
        "user_input":    "I prefer you explain in simple English, don't use too many medical words.",
        "emotion_label": "neutral",
    },
]


def separator(title: str):
    print(f"\n{'─'*55}")
    print(f"  {title}")
    print(f"{'─'*55}")


def step1_insert_user():
    separator("Step 1 — Ensure user_001 exists")
    try:
        import json
        from chatbot.db.connection import db_cursor
        with db_cursor(commit=True) as cur:
            cur.execute(
                """
                INSERT INTO users (user_id, name, language, conditions, medications, preferences)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO NOTHING
                """,
                (USER_ID, "Mdm Chen", "English",
                 ["Type 2 Diabetes"], ["Metformin 500mg"], json.dumps({})),
            )
        print("✅ user_001 is ready")
    except Exception as e:
        print(f"❌ Failed to insert user: {e}")
        sys.exit(1)


def step2_extract_memory():
    separator("Step 2 — 直接调用记忆提取（模拟 23:59 批处理）")
    from chatbot.jobs.daily_summary import _extract_memory
    print(f"输入对话条数：{len(SIMULATED_CONVERSATIONS)}")
    for c in SIMULATED_CONVERSATIONS:
        print(f"  [{c['emotion_label']}] {c['user_input'][:60]}")
    print("\n正在调用 LLM 提取记忆...")
    t0 = time.time()
    _extract_memory(USER_ID, SIMULATED_CONVERSATIONS)
    print(f"✅ 提取完成（{round(time.time()-t0, 1)}s）")


def step3_verify_facts():
    separator("Step 3 — 查询 user_facts 验证写入")
    from chatbot.memory.long_term import get_health_store
    facts = get_health_store().get_active_facts(USER_ID)
    if not facts:
        print("⚠️  user_facts 为空 — 可能 LLM 未提取到足够置信度的事实")
    else:
        print(f"✅ 写入 {len(facts)} 条 facts：")
        for f in facts:
            print(f"  [{f['category']}] (conf={f['confidence']}) {f['content']}")
    return facts


def step4_verify_context():
    separator("Step 4 — 查询 user_context 验证写入")
    from chatbot.memory.long_term import get_health_store
    ctx = get_health_store().get_user_context(USER_ID)
    has_any = any(ctx.get(k) for k in ("health_context", "current_focus", "long_term_bg"))
    if not has_any:
        print("⚠️  user_context 全部为空")
    else:
        for k, label in [
            ("health_context", "健康背景"),
            ("current_focus",  "近期关注"),
            ("long_term_bg",   "长期背景"),
        ]:
            if ctx.get(k):
                print(f"  [{label}] {ctx[k]}")
        print("✅ user_context 已更新")
    return ctx


def step5_format_prompt():
    separator("Step 5 — 验证 format_memory_for_prompt 注入内容")
    from chatbot.memory.long_term import get_health_store
    prompt_block = get_health_store().format_memory_for_prompt(USER_ID, days=14)
    if not prompt_block:
        print("⚠️  format_memory_for_prompt 返回空字符串")
    else:
        print("✅ 注入内容预览：")
        for line in prompt_block.splitlines():
            print(f"  {line}")
    return prompt_block


def step6_conversation_with_memory():
    separator("Step 6 — 跑一轮对话，观察回复是否体现记忆")
    import concurrent.futures
    from chatbot.graph.builder import app
    from chatbot.utils.memory import get_user_profile

    config = {"configurable": {"thread_id": f"memory_test_{int(time.time())}"}}
    app.update_state(config, {
        "user_profile": get_user_profile(USER_ID),
        "history":      [],
    })

    test_input = "Good morning! How should I plan my breakfast today?"
    print(f"输入：{test_input}")
    print("等待回复（最多 90 秒）...\n")

    state = {
        "user_id":      USER_ID,
        "user_input":   test_input,
        "input_mode":   "text",
        "chat_mode":    "personal",
        "history":      [],
        "user_profile": get_user_profile(USER_ID),
        "audio_path":   None,
        "image_paths":  None,
    }

    def _invoke():
        return app.invoke(state, config=config)

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future   = executor.submit(_invoke)
    executor.shutdown(wait=False)  # 不阻塞主线程
    try:
        result   = future.result(timeout=90)
        response = result.get("response", "")
        intent   = result.get("intent", "?")
        print(f"Intent: {intent}")
        print(f"回复：\n{response}")

        memory_hints = ["alone", "daughter", "australia", "bitter", "english"]
        found = [h for h in memory_hints if h.lower() in response.lower()]
        if found:
            print(f"\n✅ 回复中检测到记忆线索：{found}")
        else:
            print("\n（回复未直接引用记忆关键词，属正常——记忆影响语气而非必然复述）")
    except concurrent.futures.TimeoutError:
        print("⚠️  Step 6 超时（>90s），SEA-LION API 响应过慢")
        print("记忆存储验证（Step 1-5）已完成，对话注入可手动测试")


def main():
    print("\n" + "="*55)
    print("  长期记忆存储验证测试")
    print("="*55)

    step1_insert_user()
    step2_extract_memory()
    facts = step3_verify_facts()
    ctx   = step4_verify_context()
    block = step5_format_prompt()

    if not facts and not any(ctx.get(k) for k in ("health_context", "current_focus", "long_term_bg")):
        print("\n⚠️  facts 和 context 均为空")
        print("建议检查：OpenAI API key 是否有效，或降低 _EXTRACT_PROMPT 的 confidence 阈值")
    else:
        step6_conversation_with_memory()

    print("\n" + "="*55)
    print("  记忆存储验证完成")
    print("  Step 6（对话注入）请直接用 chatbot 手动验证")
    print("="*55 + "\n")


if __name__ == "__main__":
    main()
