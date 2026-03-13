"""
专家 Agent — 慢性病医疗顾问
数据来源：
  - 血糖 / 用药：device_sync_node 从设备直读（精确）
  - 饮食：Vision Agent 拍照识别（有图时）
  - 情绪：triage + policy（对话/语音）
  - 历史：SQLite 长期记忆 + checkpointer 短期 history
无追问链：所有数据进 agent 前已就绪，单轮回答
"""
from chatbot.state.chat_state import ChatState
from chatbot.utils.llm_factory import call_sealion_with_history_stream, format_history_for_sealion
from chatbot.memory.long_term import get_health_store
from chatbot.memory.rag.retriever import get_retriever


# ── 格式化辅助 ────────────────────────────────────────────────

def _fmt_glucose(readings: list) -> str:
    if not readings:
        return "暂无今日数据"
    return "、".join(
        f"{r.get('time', '?')} {r.get('value', '?')} mmol/L"
        for r in readings
    )


def _fmt_medication(adherence: dict) -> str:
    if not adherence:
        return "暂无记录"
    taken  = [k for k, v in adherence.items() if v]
    missed = [k for k, v in adherence.items() if not v]
    parts  = []
    if taken:  parts.append(f"已服：{', '.join(taken)}")
    if missed: parts.append(f"⚠️ 未服：{', '.join(missed)}")
    return "；".join(parts)


def _fmt_diet(vision_result: list) -> str:
    if not vision_result:
        return ""
    foods = []
    for vr in vision_result:
        if vr.get("scene_type") == "FOOD" and not vr.get("error"):
            names = [i.get("name", "") for i in vr.get("items", []) if i.get("name")]
            cal   = vr.get("total_calories_kcal", "")
            desc  = "、".join(names)
            if cal:
                desc += f"（约{cal}大卡）"
            if desc:
                foods.append(desc)
    return "；".join(foods)


# ── 主节点 ────────────────────────────────────────────────────

def expert_agent_node(state: ChatState) -> dict:
    profile     = state.get("user_profile", {})
    name        = profile.get("name", "患者")
    language    = profile.get("language", "Chinese")
    conditions  = profile.get("conditions", ["Type 2 Diabetes"])
    medications = profile.get("medications", [])
    all_intents = state.get("all_intents", ["medical"])
    user_input  = state.get("user_input", "")

    # ── 设备数据 ─────────────────────────────────────────────
    device_data  = state.get("device_data") or {}
    glucose_str  = _fmt_glucose(device_data.get("glucose", []))
    med_str      = _fmt_medication(device_data.get("medication", {}))

    # ── 饮食（Vision Agent）───────────────────────────────────
    diet_str = _fmt_diet(state.get("vision_result") or [])

    # ── 长期记忆：近7天健康记录 ──────────────────────────────
    health_history = get_health_store().format_for_llm(state["user_id"], days=7)

    # ── RAG：仅在医学相关查询时触发 ──────────────────────────
    _RAG_KEYWORDS = ["药", "血糖", "饮食", "建议", "副作用", "怎么", "为什么", "能不能",
                     "medicine", "glucose", "diet", "recommend", "why", "how"]
    rag_context = ""
    if any(kw in user_input for kw in _RAG_KEYWORDS):
        rag_query   = f"{user_input} 血糖 {glucose_str} 饮食 {diet_str}"
        rag_context = get_retriever().retrieve(rag_query, n=3)

    # ── 情绪前缀 ─────────────────────────────────────────────
    emotional_prefix = ""
    if "emotional" in all_intents or state.get("emotion_label") in ["anxious", "sad", "angry"]:
        emotional_prefix = "先用一句话回应用户情绪，再给健康建议。\n"

    policy_instruction = state.get("policy_instruction", "")

    system_prompt = (
        f"你是专业的慢性病管理医疗顾问，专注于新加坡患者。\n"
        f"患者：{name} | 病症：{', '.join(conditions)} | "
        f"处方用药：{', '.join(medications) if medications else '未记录'}\n"
        f"请用{language}回复。\n\n"
        f"【今日健康数据（设备直读）】\n"
        f"- 血糖记录：{glucose_str}\n"
        f"- 用药情况：{med_str}\n"
        f"{f'- 今餐饮食：{diet_str}' + chr(10) if diet_str else ''}"
        f"\n{health_history + chr(10) if health_history else ''}"
        f"{f'【参考医学资料】{chr(10)}{rag_context}{chr(10)}' if rag_context else ''}"
        f"{f'【用户当前状态】{policy_instruction}' + chr(10) if policy_instruction else ''}"
        f"{emotional_prefix}"
        f"请根据以上数据回答患者问题，给出具体可行的建议。\n\n"
        f"通用规则：\n"
        "- 「打卡」指健康任务打卡，不是自我伤害\n"
        f"- 结合新加坡本地饮食文化\n"
        f"- 回复150字以内"
    )

    history = format_history_for_sealion(state.get("history", []))
    history.append({"role": "user", "content": user_input})
    print("\n助手：", end="", flush=True)
    response = call_sealion_with_history_stream(system_prompt, history, reasoning=True)

    print(f"[Expert] 意图：{all_intents} | 情绪：{state.get('emotion_label', 'neutral')}")
    return {"response": response}
