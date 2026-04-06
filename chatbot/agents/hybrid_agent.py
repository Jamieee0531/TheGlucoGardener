"""
agents/hybrid_agent.py
Hybrid Agent: triggered when a medical question co-occurs with strong negative emotion.

Strategy:
- First respond to the user's emotion in one sentence (companion style)
- Then naturally transition to targeted medical advice (expert style)
- Single LLM call, merging both contexts (emotion summary + RAG)
"""
from chatbot.state.chat_state import ChatState
from chatbot.utils.llm_factory import call_sealion_with_history_stream, format_history_for_sealion
from chatbot.memory.long_term import get_health_store
from chatbot.memory.rag.lang_detect import detect_lang, LANG_NAME
from chatbot.agents.triage import consume_rag_prefetch
from chatbot.agents.glucose_reader import get_weekly_glucose_summary
import re


def _fmt_glucose(readings: list) -> str:
    if not readings:
        return ""
    return "、".join(
        f"{r.get('recorded_at', '?')[-8:-3]} {r.get('glucose', '?')} mmol/L"
        for r in readings
    )


def _fmt_weekly_glucose(records: list) -> str:
    if not records:
        return ""
    return "、".join(
        f"{r['date'][-5:]} 均{r['avg']} [{r['min']}-{r['max']}] mmol/L"
        for r in records
    )


def hybrid_agent_node(state: ChatState) -> dict:
    profile           = state.get("user_profile", {})
    name              = profile.get("name", "你")
    user_input        = state.get("user_input", "")
    emotion_label     = state.get("emotion_label", "neutral")
    emotion_intensity = state.get("emotion_intensity", "mild")
    user_id           = state["user_id"]
    language          = profile.get("language") or LANG_NAME[detect_lang(user_input)]

    # ── Emotion summary (long-term memory) ─────────────────────────────────────────
    store           = get_health_store()
    emotion_context = store.format_memory_for_prompt(user_id, days=14)

    # ── Glucose data (always fetched by hybrid) ─────────────────────────────────
    glucose_str    = _fmt_glucose(state.get("glucose_readings") or [])
    weekly_glucose = _fmt_weekly_glucose(get_weekly_glucose_summary(user_id))

    # ── RAG context ──────────────────────────────────────────────────
    rag_context = consume_rag_prefetch(user_id, user_input)

    # ── Build merged prompt ─────────────────────────────────────────────
    emotion_map = {
        "sad":     "很难受/难过",
        "fearful": "害怕/焦虑",
        "angry":   "烦躁/生气",
    }
    emotion_desc = emotion_map.get(emotion_label, emotion_label)

    # emotion_intensity determines the depth of medical content
    if emotion_intensity == "high":
        medical_instruction = (
            "第2句：只提一句最关键的数据或事实（如血糖数值），不展开建议。\n"
            "不要给建议列表，不要教导。情绪支持是重点。\n"
        )
    else:  # mild
        medical_instruction = (
            "第2-3句：自然过渡，给出1个具体、落地的建议或信息。\n"
        )

    system_prompt = (
        f"你是{name}的私人健康顾问，像一位真正了解他/她的朋友。"
        f"Reply ENTIRELY in {language}. Do not mix languages.\n\n"
        f"【当前情绪】用户现在感到{emotion_desc}（强度：{emotion_intensity}），同时有一个医疗问题。\n"
        + (f"【近期情绪历史】\n{emotion_context}\n" if emotion_context else "")
        + (f"【近1小时血糖】{glucose_str}\n" if glucose_str else "")
        + (f"【近7天血糖趋势】{weekly_glucose}\n" if weekly_glucose else "")
        + (f"【参考医学资料】\n{rag_context}\n" if rag_context else "")
        + "\n【回复结构】\n"
        "第1句：用1句话真实回应用户的具体情绪——要具体，不要泛泛安慰。\n"
        + medical_instruction
        + "全程保持朋友语气，不用「建议您」「您需要」。\n"
        "不要分段，不要bullet point，自然流动的2-3句话。\n"
        "✅ 例(mild)：'血糖反反复复真的好烦对不对 — 你今天餐后9.2，其实还在可接受范围，"
        "下次试试饭后散步15分钟。'\n"
        "✅ 例(high)：'每次看到数字都那么紧张，真的好累 — 你今天9.2，先深呼吸，这个数值我们可以慢慢调。'\n"
        "❌ 不要：'I understand how you feel. Here are some tips...'"
    )

    history = format_history_for_sealion(state.get("history", []))
    history.append({"role": "user", "content": user_input})
    print("\nAssistant: ", end="", flush=True)
    response = call_sealion_with_history_stream(system_prompt, history, reasoning=False)

    # Remove stiff phrasing
    for bad, good in [("建议您", ""), ("您需要", ""), ("应该", "可以")]:
        response = response.replace(bad, good)
    response = re.sub(r'(?m)^\s*\d+\.\s+', '- ', response).strip()

    print(f"[Hybrid Agent] emotion: {emotion_label} ({emotion_intensity})")
    return {"response": response}
