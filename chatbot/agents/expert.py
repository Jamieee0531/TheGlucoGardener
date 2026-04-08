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
    （字数由 prompt 软限制，不再硬截断）
    """
    text = text.strip()
    # 替换生硬措辞
    for bad, good in [("建议您", ""), ("您需要", ""), ("应该", "可以")]:
        text = text.replace(bad, good)

    # 把 "1. xxx\n2. xxx" 风格转成 markdown "- xxx\n- xxx"
    text = re.sub(r'(?m)^\s*\d+\.\s+', '- ', text)

    return text.strip()


# ── 主节点 ────────────────────────────────────────────────────

def expert_agent_node(state: ChatState) -> dict:
    profile     = state.get("user_profile", {})
    name        = profile.get("name", "患者")
    conditions  = profile.get("conditions", ["Type 2 Diabetes"])
    medications = profile.get("medications", [])
    all_intents = state.get("all_intents", ["medical"])
    user_input  = state.get("user_input", "")
    transcribed = state.get("transcribed_text") or ""
    lang_source = transcribed if transcribed.strip() else user_input
    language    = _detect_language(lang_source) if lang_source.strip() else profile.get("language", "Chinese")

    # ── 血糖数据 ─────────────────────────────────────────────
    glucose_str = _fmt_glucose(state.get("glucose_readings") or [])
    user_id = state["user_id"]
    weekly_glucose_str = _fmt_weekly_glucose(get_weekly_glucose_summary(user_id))
    weekly_diet_str = _fmt_weekly_diet(get_weekly_diet_history(user_id))

    # ── 饮食（Vision Agent）───────────────────────────────────
    diet_str = _fmt_diet(state.get("vision_result") or [])
    vision_failed = (
        bool(state.get("image_paths"))
        and not diet_str
        and any(vr.get("error") for vr in (state.get("vision_result") or []))
    )

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
        f"{f'【参考医学资料 — 请严格依据以下内容作出判断，不要依赖常规假设】{chr(10)}{rag_context}{chr(10)}' if rag_context else ''}"
        f"{emotion_hint}"
        + (
        f"【Food Photo Analysis Mode】\n"
        f"A food photo was uploaded. Reply in this exact structure:\n"
        f"\n"
        f"[Opening — 1 warm sentence reacting to the food like a friend seeing your lunch photo, e.g. '哇，云吞捞面！hawker 经典 lah。' Be specific to the actual dish, not generic.]\n"
        f"\n"
        f"**【食物分析】**\n"
        f"- [Dish name]: [GI level]，约[X]大卡 — [main carb/sugar source，plus why/how fast it raises blood sugar]\n"
        f"(one bullet per dish if multiple items visible)\n"
        f"\n"
        f"**【建议】**\n"
        f"- 分量/替换：[1 specific swap or portion change that's realistic for this dish]\n"
        f"- 餐后活动：[1 post-meal tip, e.g. '饭后散步15分钟 lah，血糖会稳很多']\n"
        f"\n"
        f"**【预测】**\n"
        f"- 饭后2小时血糖大概在 X–Y mmol/L。[what pushes it higher or lower]\n"
        f"\n"
        f"[Closing — 1 light, natural question that invites the user to keep chatting, e.g. '今天在哪里吃的？' or '平时喜欢加什么配料？' — match the vibe of the conversation, not scripted]\n"
        f"\n"
        f"Tone throughout: like a nutritionist friend texting after seeing your food photo — warm, specific, never preachy.\n"
        f"Use 'lah', '不妨', 'try lah', local SG food names. Each bullet 1–2 sentences max.\n"
        f"NEVER write long prose paragraphs. NEVER start with 'I understand' or 'As a diabetic'. NO disclaimers.\n"
        if diet_str else
        f"【Photo Recognition Failed Mode】\n"
        f"A photo was uploaded but couldn't be analyzed automatically (API hiccup).\n"
        f"Reply in 2 sentences: 1st — warmly acknowledge the photo with a light apology for the glitch; 2nd — ask what dish it is in a natural, curious way so you can still help.\n"
        f"✅ Example: '哎，这次识别好像出了点小问题 lah，看不太清楚是哪道菜。是什么来的？告诉我一下，我帮你分析分析！'\n"
        f"NEVER say 'API error', 'system error', or anything technical. Keep it casual and warm.\n"
        if vision_failed else
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
