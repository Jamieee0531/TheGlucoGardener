from __future__ import annotations
"""
GlucoGardener MCP Server
========================
实现 Model Context Protocol (MCP) 规范 2024-11-05
传输层：HTTP + SSE（Server-Sent Events）

端点：
  POST /mcp          → JSON-RPC 2.0 请求入口（initialize / tools/list / tools/call）
  GET  /mcp/sse      → SSE 通知流（保持连接，推送 server → client 通知）

暴露工具（Tools）：
  - search_pubmed      → NCBI E-utilities 医学文献检索
  - get_drug_info      → OpenFDA 药物说明书查询
  - search_local_rag   → 本地混合 RAG 知识库检索

启动：python -m chatbot.mcp.server（默认 port 8001）
"""
import asyncio
import json
import uuid
from typing import Any, AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn

from chatbot.mcp.tools.pubmed  import search_pubmed, format_pubmed_results
from chatbot.mcp.tools.openfda import get_drug_info, format_drug_info

# ─────────────────────────────────────────────────────────────────
# MCP 协议元信息
# ─────────────────────────────────────────────────────────────────

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {
    "name":    "GlucoGardener Medical MCP Server",
    "version": "1.0.0",
}

TOOLS_SCHEMA = [
    {
        "name":        "search_pubmed",
        "description": (
            "Search PubMed for peer-reviewed medical literature. "
            "Useful for evidence-based answers on diabetes management, drug efficacy, and clinical guidelines."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type":        "string",
                    "description": "Medical search query, e.g. 'metformin type 2 diabetes HbA1c reduction'"
                },
                "max_results": {
                    "type":    "integer",
                    "default": 3,
                    "description": "Max number of abstracts to return (1-5)"
                },
            },
            "required": ["query"],
        },
    },
    {
        "name":        "get_drug_info",
        "description": (
            "Retrieve drug label information (indications, warnings, dosage, interactions) "
            "from OpenFDA. Useful when patient asks about a specific medication."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "drug_name": {
                    "type":        "string",
                    "description": "Brand or generic name, e.g. 'metformin', 'sitagliptin'"
                },
            },
            "required": ["drug_name"],
        },
    },
    {
        "name":        "search_local_rag",
        "description": (
            "Search the local Singapore-context medical knowledge base "
            "(MOH/HPB diabetes guidelines, hawker food nutrition, local medication labels). "
            "Use this for Singapore-specific queries before PubMed."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type":        "string",
                    "description": "Query in English or Chinese"
                },
                "n": {
                    "type":    "integer",
                    "default": 3,
                    "description": "Number of knowledge chunks to retrieve"
                },
            },
            "required": ["query"],
        },
    },
]

# SSE 活跃连接池 {session_id: asyncio.Queue}
_sse_queues: dict[str, asyncio.Queue] = {}

# ─────────────────────────────────────────────────────────────────
# FastAPI 应用
# ─────────────────────────────────────────────────────────────────

app = FastAPI(title="GlucoGardener MCP Server", version="1.0.0")


@app.post("/mcp")
async def mcp_endpoint(request: Request) -> JSONResponse:
    """JSON-RPC 2.0 入口，处理所有 MCP 方法调用。"""
    try:
        body = await request.json()
    except Exception:
        return _error_response(None, -32700, "Parse error")

    rpc_id  = body.get("id")
    method  = body.get("method", "")
    params  = body.get("params", {})

    # ── initialize ───────────────────────────────────────────────
    if method == "initialize":
        return _ok_response(rpc_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "serverInfo":      SERVER_INFO,
            "capabilities":    {"tools": {}},
        })

    # ── tools/list ───────────────────────────────────────────────
    if method == "tools/list":
        return _ok_response(rpc_id, {"tools": TOOLS_SCHEMA})

    # ── tools/call ───────────────────────────────────────────────
    if method == "tools/call":
        tool_name  = params.get("name", "")
        tool_input = params.get("arguments", {})
        result     = await _dispatch_tool(tool_name, tool_input)
        return _ok_response(rpc_id, {
            "content": [{"type": "text", "text": result}],
            "isError": result.startswith("【错误】"),
        })

    # ── notifications/initialized（客户端确认，无需响应） ─────────
    if method == "notifications/initialized":
        return JSONResponse(content={}, status_code=204)

    return _error_response(rpc_id, -32601, f"Method not found: {method}")


@app.get("/mcp/sse")
async def sse_endpoint(request: Request) -> StreamingResponse:
    """
    SSE 通知流：客户端建立长连接以接收 server → client 的推送通知。
    握手后先发送 endpoint 地址，之后推送心跳保活。
    """
    session_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    _sse_queues[session_id] = queue

    async def event_stream() -> AsyncGenerator[str, None]:
        # 发送 endpoint 信息（MCP SSE 握手）
        yield _sse_event("endpoint", f"/mcp?session_id={session_id}")
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield _sse_event("message", json.dumps(data))
                except asyncio.TimeoutError:
                    yield _sse_event("ping", "keepalive")     # 心跳
        finally:
            _sse_queues.pop(session_id, None)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":               "no-cache",
            "X-Accel-Buffering":           "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


# ─────────────────────────────────────────────────────────────────
# 工具分发
# ─────────────────────────────────────────────────────────────────

async def _dispatch_tool(name: str, args: dict) -> str:
    """路由到对应工具函数，返回格式化文本。"""
    loop = asyncio.get_event_loop()

    if name == "search_pubmed":
        query       = args.get("query", "")
        max_results = min(int(args.get("max_results", 3)), 5)
        if not query:
            return "【错误】缺少 query 参数"
        articles = await loop.run_in_executor(None, search_pubmed, query, max_results)
        return format_pubmed_results(articles) or "【PubMed】未找到相关文献"

    if name == "get_drug_info":
        drug_name = args.get("drug_name", "")
        if not drug_name:
            return "【错误】缺少 drug_name 参数"
        info = await loop.run_in_executor(None, get_drug_info, drug_name)
        return format_drug_info(info)

    if name == "search_local_rag":
        query = args.get("query", "")
        n     = min(int(args.get("n", 3)), 5)
        if not query:
            return "【错误】缺少 query 参数"
        from chatbot.memory.rag.retriever import get_retriever
        result = await loop.run_in_executor(None, get_retriever().retrieve, query, n)
        return result or "【本地知识库】未找到相关内容"

    return f"【错误】未知工具：{name}"


# ─────────────────────────────────────────────────────────────────
# JSON-RPC 响应构造
# ─────────────────────────────────────────────────────────────────

def _ok_response(rpc_id: Any, result: Any) -> JSONResponse:
    return JSONResponse({"jsonrpc": "2.0", "id": rpc_id, "result": result})


def _error_response(rpc_id: Any, code: int, message: str) -> JSONResponse:
    return JSONResponse(
        {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": code, "message": message}},
        status_code=200,   # JSON-RPC 错误仍返回 HTTP 200
    )


def _sse_event(event: str, data: str) -> str:
    return f"event: {event}\ndata: {data}\n\n"


# ─────────────────────────────────────────────────────────────────
# 直接运行入口
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("chatbot.mcp.server:app", host="0.0.0.0", port=8001, reload=False)
