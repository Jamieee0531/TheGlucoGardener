"""
graph/builder.py
LangGraph 图构建

流程：
input_node → device_sync_node → triage_node → policy_node
  → [条件路由] → 各Agent → history_update → END
"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from chatbot.state.chat_state import ChatState
from chatbot.agents.triage import input_node, triage_node, route_by_intent
from chatbot.agents.device_sync import device_sync_node
from chatbot.agents.policy import policy_node
from chatbot.agents.companion import companion_agent_node
from chatbot.agents.expert import expert_agent_node
from chatbot.agents.task_forward import task_forward_node
from chatbot.agents.alert_forward import alert_forward_node
from chatbot.agents.chitchat import chitchat_agent_node
from chatbot.utils.memory import add_to_history


def history_update_node(state: ChatState) -> dict:
    """图内最后一步：把本轮对话追加到 history，由 checkpointer 持久化。"""
    user_text = state.get("user_input", "")
    response  = state.get("response", "")
    history   = add_to_history(state.get("history") or [], "user",      user_text)
    history   = add_to_history(history,                    "assistant",  response)
    return {"history": history}


def build_graph(checkpointer=None):
    graph = StateGraph(ChatState)

    # ── 注册节点 ─────────────────────────────────────────
    graph.add_node("input_node",      input_node)
    graph.add_node("device_sync",     device_sync_node)
    graph.add_node("triage_node",     triage_node)
    graph.add_node("policy_node",     policy_node)
    graph.add_node("companion_agent", companion_agent_node)
    graph.add_node("expert_agent",    expert_agent_node)
    graph.add_node("task_forward",    task_forward_node)
    graph.add_node("alert_forward",   alert_forward_node)
    graph.add_node("chitchat_agent",  chitchat_agent_node)
    graph.add_node("history_update",  history_update_node)

    # ── 入口 ─────────────────────────────────────────────
    graph.set_entry_point("input_node")

    # ── 固定边 ───────────────────────────────────────────
    graph.add_edge("input_node",  "device_sync")
    graph.add_edge("device_sync", "triage_node")
    graph.add_edge("triage_node", "policy_node")

    # ── 条件路由：policy → 各Agent ───────────────────────
    graph.add_conditional_edges(
        "policy_node",
        route_by_intent,
        {
            "companion_agent": "companion_agent",
            "expert_agent":    "expert_agent",
            "task_forward":    "task_forward",
            "alert_forward":   "alert_forward",
            "chitchat_agent":  "chitchat_agent",
        }
    )

    # ── 所有Agent → history_update → END ─────────────────
    for node in ["companion_agent", "expert_agent",
                 "task_forward", "alert_forward", "chitchat_agent"]:
        graph.add_edge(node, "history_update")
    graph.add_edge("history_update", END)

    return graph.compile(checkpointer=checkpointer)


app = build_graph(MemorySaver())
