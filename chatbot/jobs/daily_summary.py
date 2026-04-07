"""
每日情绪汇总 + 长期记忆提取定时任务
23:59 运行：
  1. 读今日 emotion_log → LLM 汇总 → 写 emotion_summary
  2. 从对话中提取结构化事实 → 写 user_facts + user_context
"""
from datetime import datetime
from chatbot.memory.long_term import get_health_store
from chatbot.utils.llm_factory import call_sealion, call_openai_json


def _summarize_emotions(entries: list) -> str:
    """调 LLM 汇总当日情绪记录，返回 summary_text。"""
    log_text = "\n".join(
        f"- [{e['emotion_label']}] {e['user_input']}"
        for e in entries
    )
    prompt = (
        f"以下是一位慢性病患者今天的情绪记录：\n{log_text}\n\n"
        "请用1-2句话总结：患者今天的整体情绪状态，以及可能的触发原因。\n"
        "只输出摘要句子，不加任何解释。"
    )
    return call_sealion(
        "你是健康管理系统的记录员，负责简洁记录患者每日情绪状态。",
        prompt,
    )


_EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "facts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category":   {"type": "string", "enum": ["social", "lifestyle", "emotion_trigger", "event", "preference"]},
                    "content":    {"type": "string"},
                    "confidence": {"type": "number"},
                },
                "required": ["category", "content", "confidence"],
                "additionalProperties": False,
            },
        },
        "health_context": {"type": "string"},
        "current_focus":  {"type": "string"},
        "long_term_bg":   {"type": "string"},
    },
    "required": ["facts", "health_context", "current_focus", "long_term_bg"],
    "additionalProperties": False,
}

_EXTRACT_PROMPT = """\
You are a memory extractor for a chronic illness health chatbot. Read the user's conversation history below and extract:

1. facts: Specific, stable personal facts (confidence ≥ 0.75 only). Categories:
   - social: family relationships, living situation, support network
   - lifestyle: daily habits, diet preferences, activities
   - preference: communication style, language, format preferences
   - emotion_trigger: recurring emotional patterns, what makes them sad/anxious/happy
   - event: specific one-time events (use sparingly)

2. health_context: 1-2 sentence summary of patient's health management situation right now
3. current_focus: What the patient is most worried about or dealing with currently (1 sentence)
4. long_term_bg: Stable background facts as a brief paragraph (family, lifestyle, preferences)

Rules:
- Only extract facts explicitly stated, not inferred
- confidence: 0.9 = clearly stated, 0.75 = reasonably implied
- Keep content concise (under 20 words per fact)
- If nothing meaningful to extract for a field, return empty string ""

Conversation:
"""


def _extract_memory(user_id: str, conversations: list) -> None:
    """
    从对话列表中提取结构化长期记忆，写入 user_facts 和 user_context。
    conversations: list of {"user_input": str, "emotion_label": str}
    """
    if not conversations:
        return

    conv_text = "\n".join(
        f"[{c['emotion_label']}] {c['user_input']}"
        for c in conversations
    )

    try:
        result = call_openai_json(_EXTRACT_PROMPT + conv_text, _EXTRACT_SCHEMA)
    except Exception as e:
        print(f"[ExtractMemory] LLM 调用失败（{e}），跳过记忆提取")
        return

    store = get_health_store()

    # ── 写入 user_facts ───────────────────────────────────────
    facts = result.get("facts", [])
    written = 0
    for fact in facts:
        if fact.get("confidence", 0) >= 0.75 and fact.get("content"):
            try:
                store.upsert_fact(
                    user_id=user_id,
                    category=fact["category"],
                    content=fact["content"],
                    confidence=fact["confidence"],
                )
                written += 1
            except Exception as e:
                print(f"[ExtractMemory] fact 写入失败（{e}）: {fact['content'][:40]}")
    print(f"[ExtractMemory] {user_id}: 写入 {written}/{len(facts)} 条 facts")

    # ── 写入 user_context ─────────────────────────────────────
    health_context = result.get("health_context") or None
    current_focus  = result.get("current_focus") or None
    long_term_bg   = result.get("long_term_bg") or None

    if any([health_context, current_focus, long_term_bg]):
        try:
            store.upsert_context(
                user_id=user_id,
                health_context=health_context,
                current_focus=current_focus,
                long_term_bg=long_term_bg,
            )
            print(f"[ExtractMemory] {user_id}: user_context 已更新")
        except Exception as e:
            print(f"[ExtractMemory] user_context 写入失败（{e}）")


def run_daily_summary() -> None:
    """遍历今日有情绪记录的用户，逐个汇总情绪并提取长期记忆。"""
    store = get_health_store()
    today = datetime.now().strftime("%Y-%m-%d")
    user_ids = store.get_today_emotion_user_ids()

    if not user_ids:
        print("[DailySummary] 今日无情绪记录，跳过")
        return

    for user_id in user_ids:
        entries = store.get_today_emotions(user_id)
        if not entries:
            continue

        # 1. 情绪汇总
        text = _summarize_emotions(entries)
        store.save_emotion_summary(user_id, text, today)
        print(f"[DailySummary] {user_id} 情绪汇总：{text[:40]}…")

        # 2. 长期记忆提取
        _extract_memory(user_id, entries)

    print(f"[DailySummary] 共处理 {len(user_ids)} 位用户")
