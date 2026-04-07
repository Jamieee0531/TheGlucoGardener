"""
MCP Tool: OpenFDA 药物信息查询
使用 OpenFDA Drug Label API（免费，无需 API Key）
文档：https://open.fda.gov/apis/drug/label/

返回格式：{"drug_name": str, "indications": str, "warnings": str,
           "dosage": str, "interactions": str, "source": "OpenFDA"}
"""
from __future__ import annotations
import httpx

OPENFDA_URL = "https://api.fda.gov/drug/label.json"
TIMEOUT     = 10.0


def get_drug_info(drug_name: str) -> dict:
    """
    查询药物说明书信息（适应症、警告、用量、药物相互作用）。
    未找到时返回 {"error": "..."} 。
    """
    try:
        params = {
            "search": f'openfda.brand_name:"{drug_name}" OR openfda.generic_name:"{drug_name}"',
            "limit":  1,
        }
        resp = httpx.get(OPENFDA_URL, params=params, timeout=TIMEOUT)

        if resp.status_code == 404:
            # 退回到宽松搜索
            params["search"] = drug_name
            resp = httpx.get(OPENFDA_URL, params=params, timeout=TIMEOUT)

        resp.raise_for_status()
        results = resp.json().get("results", [])
        if not results:
            return {"error": f"未找到药物：{drug_name}"}

        label = results[0]
        return {
            "drug_name":    drug_name,
            "indications":  _first(label, "indications_and_usage"),
            "warnings":     _first(label, "warnings") or _first(label, "warnings_and_cautions"),
            "dosage":       _first(label, "dosage_and_administration"),
            "interactions": _first(label, "drug_interactions"),
            "source":       "OpenFDA",
        }
    except Exception as e:
        print(f"[OpenFDA] 查询失败：{e}")
        return {"error": str(e)}


def format_drug_info(info: dict) -> str:
    """将药物信息格式化为 LLM 可读文本。"""
    if "error" in info:
        return f"【药物查询】{info['error']}"
    parts = [f"【{info['drug_name']} 药物说明（来源：OpenFDA）】"]
    if info["indications"]:
        parts.append(f"适应症：{info['indications'][:200]}…")
    if info["warnings"]:
        parts.append(f"警告：{info['warnings'][:200]}…")
    if info["dosage"]:
        parts.append(f"用量：{info['dosage'][:150]}…")
    if info["interactions"]:
        parts.append(f"药物相互作用：{info['interactions'][:150]}…")
    return "\n".join(parts)


def _first(label: dict, key: str) -> str:
    val = label.get(key)
    if isinstance(val, list) and val:
        return val[0].strip()
    if isinstance(val, str):
        return val.strip()
    return ""
