from __future__ import annotations
"""
GlucoGardener MCP Client
========================
通过 JSON-RPC 2.0 over HTTP 调用 MCP Server 暴露的工具。

使用方式：
    client = MCPClient("http://localhost:8001")
    result = client.call_tool("search_pubmed", {"query": "metformin HbA1c", "max_results": 3})

亦支持并发调用（call_tools_parallel），用于同时拉取 PubMed + OpenFDA。
"""
from __future__ import annotations
import concurrent.futures
import json
import uuid
from typing import Any

import httpx

DEFAULT_MCP_URL = "http://localhost:8001"
TIMEOUT = 15.0


class MCPClient:
    """同步 MCP 客户端（内部用 httpx 同步调用，适合在线程池中运行）。"""

    def __init__(self, base_url: str = DEFAULT_MCP_URL):
        self.base_url = base_url.rstrip("/")
        self._initialized = False

    def _post(self, method: str, params: dict | None = None) -> Any:
        payload = {
            "jsonrpc": "2.0",
            "id":      str(uuid.uuid4()),
            "method":  method,
            "params":  params or {},
        }
        resp = httpx.post(
            f"{self.base_url}/mcp",
            json=payload,
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"MCP error {data['error']['code']}: {data['error']['message']}")
        return data.get("result")

    def initialize(self) -> dict:
        """握手，获取 server 能力。"""
        result = self._post("initialize", {
            "protocolVersion": "2024-11-05",
            "clientInfo": {"name": "GlucoGardener-Expert-Agent", "version": "1.0.0"},
            "capabilities": {},
        })
        self._initialized = True
        return result

    def list_tools(self) -> list[dict]:
        """列出所有可用工具及其 schema。"""
        return self._post("tools/list").get("tools", [])

    def call_tool(self, tool_name: str, arguments: dict) -> str:
        """
        调用单个工具，返回文本结果。
        server 端保证 content[0].text 始终存在。
        """
        result = self._post("tools/call", {
            "name":      tool_name,
            "arguments": arguments,
        })
        content = result.get("content", [])
        if content and content[0].get("type") == "text":
            return content[0]["text"]
        return ""

    def call_tools_parallel(
        self,
        calls: list[tuple[str, dict]],
        max_workers: int = 3,
    ) -> list[str]:
        """
        并发调用多个工具，按 calls 顺序返回结果列表。
        calls: [(tool_name, arguments), ...]
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [
                pool.submit(self.call_tool, name, args)
                for name, args in calls
            ]
            results = []
            for f in futures:
                try:
                    results.append(f.result(timeout=TIMEOUT))
                except Exception as e:
                    print(f"[MCP Client] 工具调用失败：{e}")
                    results.append("")
        return results


# ─────────────────────────────────────────────────────────────────
# 单例（Expert Agent 直接 import 使用）
# ─────────────────────────────────────────────────────────────────

_client: MCPClient | None = None


def get_mcp_client(base_url: str = DEFAULT_MCP_URL) -> MCPClient:
    global _client
    if _client is None:
        _client = MCPClient(base_url)
    return _client


# ─────────────────────────────────────────────────────────────────
# 便捷函数：Expert Agent 内直接调用
# ─────────────────────────────────────────────────────────────────

def fetch_medical_context(user_input: str, drug_mentions: list[str] | None = None) -> str:
    """
    Expert Agent 调用入口：
      1. 并发拉取 PubMed 文献 + 本地 RAG
      2. 若用户提及药物名，同时拉取 OpenFDA 信息
    返回拼接后的参考资料文本（注入 system prompt）。
    """
    client = get_mcp_client()

    calls: list[tuple[str, dict]] = [
        ("search_pubmed",    {"query": f"{user_input} diabetes Singapore", "max_results": 2}),
        ("search_local_rag", {"query": user_input, "n": 3}),
    ]
    if drug_mentions:
        for drug in drug_mentions[:2]:      # 最多查 2 种药物
            calls.append(("get_drug_info", {"drug_name": drug}))

    try:
        results = client.call_tools_parallel(calls)
    except Exception as e:
        print(f"[MCP Client] fetch_medical_context 失败，降级到本地 RAG：{e}")
        # 降级：直接用本地 RAG
        from chatbot.memory.rag.retriever import get_retriever
        return get_retriever().retrieve(user_input, 3)

    return "\n\n".join(r for r in results if r).strip()
