from __future__ import annotations
"""
MCP Tool: PubMed 医学文献检索
使用 NCBI E-utilities API（免费，无需 API Key）
- esearch: 关键词 → PMID 列表
- efetch:  PMID   → 摘要全文

返回格式：[{"pmid": str, "title": str, "abstract": str, "journal": str, "year": str}]
"""
import re
import time
import xml.etree.ElementTree as ET
import httpx

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
TIMEOUT     = 10.0
NCBI_EMAIL  = "glucogardener@example.com"  # NCBI 要求提供联系邮件


def search_pubmed(query: str, max_results: int = 3) -> list[dict]:
    """
    检索 PubMed，返回 max_results 篇摘要。
    query 建议附加 "diabetes" 等主题词以提升相关性。
    """
    try:
        pmids = _esearch(query, max_results)
        if not pmids:
            return []
        time.sleep(0.34)          # NCBI 限速：≤3 req/s
        articles = _efetch(pmids)
        return articles
    except Exception as e:
        print(f"[PubMed] 检索失败：{e}")
        return []


def format_pubmed_results(articles: list[dict]) -> str:
    """将 PubMed 结果格式化为 LLM 可读的参考资料文本。"""
    if not articles:
        return ""
    lines = ["【PubMed 最新循证依据】"]
    for i, a in enumerate(articles, 1):
        abstract_snippet = a["abstract"][:300] + "…" if len(a["abstract"]) > 300 else a["abstract"]
        lines.append(
            f"{i}. {a['title']} ({a['journal']}, {a['year']}) [PMID:{a['pmid']}]\n"
            f"   {abstract_snippet}"
        )
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────
# 内部实现
# ─────────────────────────────────────────────────────────────────

def _esearch(query: str, max_results: int) -> list[str]:
    """返回 PMID 字符串列表。"""
    params = {
        "db":       "pubmed",
        "term":     query,
        "retmax":   max_results,
        "retmode":  "json",
        "sort":     "relevance",
        "email":    NCBI_EMAIL,
    }
    resp = httpx.get(ESEARCH_URL, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()["esearchresult"].get("idlist", [])


def _efetch(pmids: list[str]) -> list[dict]:
    """批量拉取 PubMedArticle XML，解析标题/摘要/期刊/年份。"""
    params = {
        "db":       "pubmed",
        "id":       ",".join(pmids),
        "rettype":  "abstract",
        "retmode":  "xml",
        "email":    NCBI_EMAIL,
    }
    resp = httpx.get(EFETCH_URL, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    return _parse_pubmed_xml(resp.text)


def _parse_pubmed_xml(xml_text: str) -> list[dict]:
    root     = ET.fromstring(xml_text)
    articles = []
    for article in root.findall(".//PubmedArticle"):
        pmid     = _get_text(article, ".//PMID")
        title    = _get_text(article, ".//ArticleTitle")
        abstract = " ".join(
            t.text or "" for t in article.findall(".//AbstractText")
        ).strip()
        journal  = _get_text(article, ".//Journal/Title") or _get_text(article, ".//ISOAbbreviation")
        year     = _get_text(article, ".//PubDate/Year") or _get_text(article, ".//MedlineDate")[:4]
        # 清理 XML 残留标签
        title    = re.sub(r"<[^>]+>", "", title)
        abstract = re.sub(r"<[^>]+>", "", abstract)
        articles.append({
            "pmid":     pmid,
            "title":    title,
            "abstract": abstract or "No abstract available.",
            "journal":  journal,
            "year":     year,
        })
    return articles


def _get_text(node, xpath: str) -> str:
    el = node.find(xpath)
    return (el.text or "").strip() if el is not None else ""
