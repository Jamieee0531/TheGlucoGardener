"""
陪伴Agent，用Qwen对话模型
接收policy指令决定回复风格
内置心理危机关键词检测
长期记忆：读取近期情绪摘要注入 prompt，回复后生成本轮摘要并存储
"""
import re
from datetime import datetime
from chatbot.state.chat_state import ChatState
from chatbot.utils.llm_factory import (
    call_sealion, call_sealion_with_history_stream, format_history_for_sealion
)
from chatbot.memory.long_term import get_health_store

# 用 regex 覆盖变体（"活着没什么意思"、"不想活了" 等）
_CRISIS_PATTERNS = [
    r"活着.*没.*意思", r"不想.*活", r"去死", r"伤害.*自己", r"结束.*生命",
    r"no\s*point\s*living", r"want\s*to\s*die", r"hurt\s*myself", r"end\s*my\s*life",
]

NEGATIVE_EMOTIONS = {"sad", "anxious", "angry", "scared"}


def _is_crisis(text: str) -> bool:
    return any(re.search(p, text) for p in _CRISIS_PATTERNS)


def _generate_emotion_summary(user_input: str, response: str, emotion_label: str) -> str:
    """调 LLM 生成本轮情绪摘要（1-2句），存入长期记忆。"""
    prompt = (
        f"以下是一段患者和助手的对话片段：\n"
        f"患者说：{user_input}\n"
        f"情绪标签：{emotion_label}\n\n"
        "用1-2句话总结：患者当前的情绪状态，以及可能的触发原因或背景事件。"
        "只输出摘要句子，不加任何解释。"
    )
    try:
        return call_sealion("你是健康管理系统的记录员，负责简洁记录患者情绪状态。", prompt)
    except Exception:
        return f"患者情绪：{emotion_label}，输入：{user_input[:50]}"


def companion_agent_node(state: ChatState) -> dict:
    profile            = state.get("user_profile", {})
    name               = profile.get("name", "您")
    language           = profile.get("language", "Chinese")
    user_input         = state["user_input"]
    emotion_label      = state.get("emotion_label", "neutral")
    policy_instruction = state.get("policy_instruction", "")
    user_id            = state["user_id"]

    # 心理危机检测
    if _is_crisis(user_input):
        response = (
            f"{name}，您刚才说的话让我很担心。"
            "您的生命很重要，您不需要一个人扛着这些。"
            "请拨打新加坡心理援助热线：1-767（24小时）或 IMH：6389 2222。"
            "我在这里陪您——能告诉我，是什么让您有这样的感受吗？"
        ) if language != "English" else (
            "I'm really concerned about what you said. You matter and you're not alone. "
            "Please call Samaritans of Singapore: 1-767 (24hr) or IMH: 6389 2222."
        )
        print(f"\n助手：{response}")
        print(f"[陪伴Agent] ⚠️ 心理危机检测触发")
        return {
            "response": response,
            "emotion_log": {
                "user_id": user_id, "timestamp": datetime.now().isoformat(),
                "input": user_input, "emotion_label": "crisis", "is_crisis": True,
            },
            "alert_trigger": {
                "user_id": user_id, "timestamp": datetime.now().isoformat(),
                "alert_input": user_input, "severity": "心理危机",
            },
        }

    # ── 读取近期情绪摘要（长期记忆）────────────────────────────
    store           = get_health_store()
    emotion_context = store.format_emotion_summary_for_llm(user_id, days=14)

    system_prompt = (
        f"你是温暖、有耐心的健康陪伴助手，陪伴新加坡的慢性病患者。\n"
        f"患者姓名：{name}，请用{language}回复。\n"
        f"{emotion_context + chr(10) if emotion_context else ''}"
        f"{f'【用户当前状态】{policy_instruction}' + chr(10) if policy_instruction else ''}"
        "通用原则：\n"
        "- 回复60字以内，越短越好\n"
        "- 不提供具体医疗建议\n"
        "- 不一定每次都要问问题，有时候只是陪着就够了\n"
        "- 像朋友一样说话，不要像顾问"
    )

    history = format_history_for_sealion(state.get("history", []))
    history.append({"role": "user", "content": user_input})
    print("\n助手：", end="", flush=True)
    response = call_sealion_with_history_stream(system_prompt, history)

    # ── 写入情绪摘要（长期记忆，仅负面情绪，每天一次）──────────
    if emotion_label in NEGATIVE_EMOTIONS:
        today     = datetime.now().strftime("%Y-%m-%d")
        has_today = any(
            s["timestamp"].startswith(today)
            for s in store.get_emotion_summaries(user_id, days=1)
        )
        if not has_today:
            summary = _generate_emotion_summary(user_input, response, emotion_label)
            store.log_event(user_id, "emotion_summary", {
                "text":    summary,
                "emotion": emotion_label,
            })
            print(f"[陪伴Agent] 今日情绪摘要已存储：{summary[:40]}…")
        else:
            print(f"[陪伴Agent] 今日摘要已存在，跳过生成")

    emotion_log = {
        "user_id": user_id, "timestamp": datetime.now().isoformat(),
        "input": user_input, "emotion_label": emotion_label,
        "agent_response": response, "is_crisis": False,
    }

    print(f"[陪伴Agent] 情绪：{emotion_label}")
    return {"response": response, "emotion_log": emotion_log}
