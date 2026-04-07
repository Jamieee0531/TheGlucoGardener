"""
graph/builder.py
LangGraph 图构建

流程：
input_node → glucose_reader → triage_node
  → [条件路由] → companion_agent / expert_agent / hybrid_agent / crisis_agent
               → history_update → END
"""
import sqlite3
from pathlib import Path
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from chatbot.state.chat_state import ChatState
from chatbot.agents.triage import input_node
from chatbot.agents.triage_gemini import triage_node_gemini
from chatbot.agents.glucose_reader import glucose_reader_node
from chatbot.agents.companion import companion_agent_node
from chatbot.agents.expert import expert_agent_node
from chatbot.agents.hybrid_agent import hybrid_agent_node
from chatbot.agents.crisis import crisis_agent_node
from chatbot.utils.memory import add_to_history


def history_update_node(state: ChatState) -> dict:
    """图内最后一步：把本轮对话追加到 history，由 checkpointer 持久化。"""
    user_text = state.get("user_input", "")
    response  = state.get("response", "")
    # Annotated[list, operator.add]：只返回新增的条目，LangGraph 自动追加
    new_entries = []
    if user_text:
        new_entries.append({"role": "user", "content": user_text})
    if response:
        new_entries.append({"role": "assistant", "content": response})
    return {"history": new_entries}


def _route_by_intent(state: ChatState) -> str:
    intent = state.get("intent", "companion")
    return {
        "medical":   "expert_agent",
        "hybrid":    "hybrid_agent",
        "crisis":    "crisis_agent",
    }.get(intent, "companion_agent")


def build_graph(checkpointer=None):
    graph = StateGraph(ChatState)

    # ── 注册节点 ─────────────────────────────────────────
    graph.add_node("input_node",      input_node)
    graph.add_node("glucose_reader",  glucose_reader_node)
    graph.add_node("triage_node",     triage_node_gemini)
    graph.add_node("companion_agent", companion_agent_node)
    graph.add_node("expert_agent",    expert_agent_node)
    graph.add_node("hybrid_agent",    hybrid_agent_node)
    graph.add_node("crisis_agent",    crisis_agent_node)
    graph.add_node("history_update",  history_update_node)

    # ── 入口 ─────────────────────────────────────────────
    graph.set_entry_point("input_node")

    # ── 固定边 ───────────────────────────────────────────
    graph.add_edge("input_node",     "glucose_reader")
    graph.add_edge("glucose_reader", "triage_node")

    # ── 条件路由：triage → companion / expert / hybrid / crisis
    graph.add_conditional_edges(
        "triage_node",
        _route_by_intent,
        {
            "companion_agent": "companion_agent",
            "expert_agent":    "expert_agent",
            "hybrid_agent":    "hybrid_agent",
            "crisis_agent":    "crisis_agent",
        }
    )

    # ── 所有 Agent → history_update → END ────────────────
    for node in ["companion_agent", "expert_agent", "hybrid_agent", "crisis_agent"]:
        graph.add_edge(node, "history_update")
    graph.add_edge("history_update", END)

    return graph.compile(checkpointer=checkpointer)


_DB_PATH = Path(__file__).parent.parent.parent / "data" / "langgraph.db"
_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
_conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
app   = build_graph(SqliteSaver(_conn))
