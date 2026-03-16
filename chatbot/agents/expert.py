"""
专家 Agent — 慢性病医疗顾问
数据来源：
  - 血糖：glucose_reader_node 从共享DB直读（精确）
  - 饮食：Vision Agent 拍照识别（有图时）
  - 情绪：triage + policy（对话/语音）
  - 历史：SQLite 长期记忆 + checkpointer 短期 history
无追问链：所有数据进 agent 前已就绪，单轮回答
"""
from chatbot.state.chat_state import ChatState
from chatbot.utils.llm_factory import call_sealion_with_history_stream, format_history_for_sealion
from chatbot.memory.long_term import get_health_store
from chatbot.agents.triage import consume_rag_prefetch
import re
from chatbot.agents.glucose_reader import get_weekly_glucose_summary, get_weekly_diet_history


def _detect_language(text: str) -> str:
    """Detect if input is primarily English or Chinese."""
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    ascii_letters  = len(re.findall(r'[a-zA-Z]', text))
    return "English" if ascii_letters > chinese_chars else "Chinese"


# ── 格式化辅助 ────────────────────────────────────────────────

def _fmt_glucose(readings: list) -> str:
    if not readings:
        return "暂无近1小时数据"
    return "、".join(
        f"{r.get('recorded_at', '?')[-8:-3]} {r.get('glucose', '?')} mmol/L"
        for r in readings
    )


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


def _fmt_weekly_glucose(records: list) -> str:
    if not records:
        return ""
    return "、".join(
        f"{r['date'][-5:]} 均{r['avg']} [{r['min']}-{r['max']}] mmol/L"
        for r in records
    )


def _fmt_weekly_diet(records: list) -> str:
    if not records:
        return ""
    return "\n".join(f"  {r['date'][-5:]}：{r['meals']}" for r in records)


def _clean_response(text: str) -> str:
    """
    清理模型输出：
    - 去掉生硬措辞
    - 数字列表转 Markdown 无序列表
    - 超过3句时截断，保留前3句
    """
    text = text.strip()
    # 替换生硬措辞
    for bad, good in [("建议您", ""), ("您需要", ""), ("应该", "可以")]:
        text = text.replace(bad, good)

    # 把 "1. xxx\n2. xxx" 风格转成 markdown "- xxx\n- xxx"
    text = re.sub(r'(?m)^\s*\d+\.\s+', '- ', text)

    # 超过3句截断
    parts = re.split(r'(?<=[。！？!?])', text)
    parts = [p for p in parts if p.strip()]
    if len(parts) > 3:
        # 如果有列表项，保留列表完整
        has_list = any(p.strip().startswith('-') for p in parts)
        if not has_list:
            text = "".join(parts[:3]).strip()

    return text.strip()


# ── 主节点 ────────────────────────────────────────────────────

def expert_agent_node(state: ChatState) -> dict:
    profile     = state.get("user_profile", {})
    name        = profile.get("name", "患者")
    conditions  = profile.get("conditions", ["Type 2 Diabetes"])
    medications = profile.get("medications", [])
    all_intents = state.get("all_intents", ["medical"])
    user_input  = state.get("user_input", "")
    language    = _detect_language(user_input) if user_input.strip() else profile.get("language", "Chinese")

    # ── 血糖数据 ─────────────────────────────────────────────
    glucose_str = _fmt_glucose(state.get("glucose_readings") or [])
    user_id = state["user_id"]
    weekly_glucose_str = _fmt_weekly_glucose(get_weekly_glucose_summary(user_id))
    weekly_diet_str = _fmt_weekly_diet(get_weekly_diet_history(user_id))

    # ── 饮食（Vision Agent）───────────────────────────────────
    diet_str = _fmt_diet(state.get("vision_result") or [])

    # ── RAG：仅在医学相关查询时触发 ──────────────────────────
    _RAG_KEYWORDS = ["药", "血糖", "饮食", "建议", "副作用", "怎么", "为什么", "能不能",
                     "头晕", "头痛", "恶心", "症状", "不舒服", "害怕", "心跳",
                     "medicine", "glucose", "diet", "recommend", "why", "how",
                     "dizzy", "dizziness", "blood sugar", "sugar", "symptom",
                     "nausea", "scared", "blurry", "shaky", "sweat", "pain",
                     "stand", "pressure", "bp", "low", "high"]
    rag_context = ""
    if any(kw in user_input for kw in _RAG_KEYWORDS):
        rag_query   = f"{user_input} 血糖 {glucose_str} 饮食 {diet_str}"
        rag_context = consume_rag_prefetch(user_id, rag_query)

    emotion_label = state.get("emotion_label", "neutral")
    emotion_hint  = f"【当前情绪】{emotion_label}\n" if emotion_label != "neutral" else ""

    system_prompt = (
        f"你是{name}的私人健康顾问，像一位温暖、专业的朋友，专注于新加坡慢性病管理。\n"
        f"患者：{name} | 病症：{', '.join(conditions)} | "
        f"处方用药：{', '.join(medications) if medications else '未记录'}\n"
        f"Reply ENTIRELY in {language}. Do not mix languages in a single response.\n\n"
        f"【近1小时血糖】\n"
        f"- 记录：{glucose_str}\n"
        f"{f'- 当餐饮食：{diet_str}{chr(10)}' if diet_str else ''}"
        f"{f'【近7天血糖趋势】{chr(10)}- {weekly_glucose_str}{chr(10)}' if weekly_glucose_str else ''}"
        f"{f'【近7天饮食历史】{chr(10)}{weekly_diet_str}{chr(10)}' if weekly_diet_str else ''}"
        f"{f'【参考医学资料】{chr(10)}{rag_context}{chr(10)}' if rag_context else ''}"
        f"{emotion_hint}"
        + (
        f"【Food Photo Analysis Mode】\n"
        f"A food photo was uploaded. Give a friendly nutritional breakdown like this:\n"
        f"1. Name each dish and its approximate carbs/GI impact in plain language (1 line each)\n"
        f"2. One specific swap or adjustment suggestion (e.g. 'less rice, more veg')\n"
        f"3. Rough prediction: 'your 2-hour post-meal blood sugar might be around X mmol/L'\n"
        f"Tone: like a friend who knows nutrition, not a clinical report. Use 'lah', 'try', 'maybe'.\n"
        f"Never start with 'I understand' or 'As a diabetic'.\n"
        f"Never add disclaimers like 'I am an AI' or 'consult a healthcare professional' — absolutely forbidden.\n"
        if diet_str else
        f"【回复规则】\n"
        f"只说2句话：第1句回应患者感受，第2句给一个落地建议。\n"
        f"❌ Wrong: 'I understand you're wondering... You should reduce portion size and add vegetables.'\n"
        f"✅ Right: 'Wanton mee is tricky lah — the noodles add up fast. Try asking for less noodles and add some chye sim on the side?'\n"
        f"When user reports a symptom with fear or uncertainty: warm acknowledgment of the SPECIFIC fear + ONE clarifying question. No advice yet.\n"
        f"✅ Right: 'Aiyoh, that kind of sudden dizzy is really scary lah — glad you sat back down. Was it only when you stood up, or did it stay even after sitting?'\n"
        f"❌ Wrong: 'That must have been worrying. Was the dizziness...' — too flat, doesn't match the fear.\n"
        f"❌ Wrong: asking a question AND giving advice in the same turn.\n"
        f"Only give advice AFTER the user has answered your clarifying question.\n"
        f"CRITICAL: Do NOT suggest eating snacks or food for dizziness when standing up — that is postural hypotension, not low blood sugar. Food does NOT help. Correct advice: stand up slowly, drink water.\n"
        f"Only recommend eating if blood sugar is confirmed below 3.9 mmol/L.\n"
        f"Never start with 'I understand', 'That's a great question', 'As a diabetic', 'That's a sign of'. Jump straight in with warmth.\n"
        f"No bullet points. Use 「试试/不妨/先...看看」not 「建议您/您需要」.\n"
        f"「打卡」=健康任务打卡。可结合新加坡本地饮食（如hawker food）。"
        )
    )

    history = format_history_for_sealion(state.get("history", []))
    history.append({"role": "user", "content": user_input})
    print("\n助手：", end="", flush=True)
    response = call_sealion_with_history_stream(system_prompt, history, reasoning=False)
    if not diet_str:
        response = _clean_response(response)

    print(f"[Expert] 意图：{all_intents} | 情绪：{emotion_label}")
    return {"response": response}
