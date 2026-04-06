"""
RAG 独立评测脚本
================
评测逻辑：
  1. 对每个 case，用 retriever 检索上下文
  2. 用 LLM（SEA-LION）判断上下文是否覆盖 required_concepts
  3. 输出覆盖率分数（0.0 - 1.0）和详细报告

评测指标：
  - Context Coverage：检索到的上下文覆盖了多少 required_concepts
  - Empty Rate：out_of_scope case 正确返回空的比例
  - 按语言/类别分组统计

用法：
  python tests/run_rag_eval.py                     # 全量评测
  python tests/run_rag_eval.py --type single       # 仅单轮
  python tests/run_rag_eval.py --category food     # 仅某类别
  python tests/run_rag_eval.py --no-llm            # 跳过 LLM 裁判，只看检索结果
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# 加载 .env（Windows PowerShell 下不会自动注入环境变量）
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

DATASET_PATH = Path(__file__).parent / "rag_eval_dataset.json"
RESULTS_PATH = Path(__file__).parent / "rag_eval_results.json"

# LLM 裁判 prompt
_JUDGE_PROMPT = """You are evaluating a medical RAG system. Given a patient query and retrieved context, determine how many of the required concepts are covered by the context.

Query: {query}

Retrieved Context:
{context}

Required Concepts (these are what the context SHOULD contain to answer the query):
{concepts}

For each required concept, answer YES if the context contains information that covers this concept, or NO if it does not.
Return a JSON object: {{"results": [{{"concept": "...", "covered": true/false, "evidence": "brief quote or 'not found'"}}]}}
Return ONLY the JSON, no other text."""


@dataclass
class EvalResult:
    case_id:        str
    query:          str
    lang:           str
    category:       str
    context:        str
    coverage_score: float          = 0.0   # 0.0 - 1.0
    concept_results: list[dict]    = field(default_factory=list)
    is_empty:       bool           = False
    expect_empty:   bool           = False
    error:          str            = ""


def load_dataset() -> list[dict]:
    text = DATASET_PATH.read_text(encoding="utf-8")
    # 去掉 JSON 注释（// ...）
    import re
    text = re.sub(r"//[^\n]*", "", text)
    return json.loads(text)["cases"]


def run_eval(
    cases:      list[dict],
    use_llm:    bool = True,
    n_retrieve: int  = 3,
) -> list[EvalResult]:
    from chatbot.memory.rag.retriever import get_retriever

    retriever = get_retriever()
    retriever._init()

    results: list[EvalResult] = []

    for case in cases:
        case_id     = case["id"]
        lang        = case.get("lang", "English")
        category    = case.get("category", "general")
        expect_empty = case.get("expect_empty", False)
        concepts    = case.get("required_concepts", [])

        # 多轮对话：把历史拼进 query
        if case.get("type") == "multi" and case.get("history"):
            history_text = " | ".join(
                f"{h['role']}: {h['content']}" for h in case["history"]
            )
            retrieval_query = f"{history_text} | user: {case['query']}"
        else:
            retrieval_query = case["query"]

        print(f"\n[{case_id}] {case['query'][:60]}...")

        # 检索
        context = retriever.retrieve(retrieval_query, n=n_retrieve, lang=lang)
        is_empty = not bool(context)

        result = EvalResult(
            case_id      = case_id,
            query        = case["query"],
            lang         = lang,
            category     = category,
            context      = context,
            is_empty     = is_empty,
            expect_empty = expect_empty,
        )

        # out_of_scope case
        if expect_empty:
            result.coverage_score = 1.0 if is_empty else 0.0
            status = "✅" if is_empty else "❌"
            print(f"  {status} 超出范围保护：{'正确返回空' if is_empty else '错误返回了内容'}")
            results.append(result)
            continue

        if is_empty:
            result.coverage_score = 0.0
            result.error = "检索返回空（阈值过滤或知识库缺失）"
            print(f"  ❌ 无检索结果")
            results.append(result)
            continue

        print(f"  检索到上下文（{len(context)} 字符）")

        # LLM 裁判
        if use_llm and concepts:
            concept_results = judge_with_llm(case["query"], context, concepts)
            if concept_results:
                covered = sum(1 for c in concept_results if c.get("covered"))
                result.coverage_score  = covered / len(concepts)
                result.concept_results = concept_results
                print(f"  覆盖率：{covered}/{len(concepts)} = {result.coverage_score:.0%}")
                for cr in concept_results:
                    icon = "✅" if cr.get("covered") else "❌"
                    print(f"    {icon} {cr['concept'][:60]}")
            else:
                result.error = "LLM 裁判失败"
                result.coverage_score = -1.0
        else:
            # 不用 LLM：简单检查 concepts 关键词是否在上下文中
            context_lower = context.lower()
            covered_count = 0
            for concept in concepts:
                # 取概念里的核心词检查
                core_words = [w for w in concept.lower().split() if len(w) > 4]
                if any(w in context_lower for w in core_words):
                    covered_count += 1
            result.coverage_score = covered_count / len(concepts) if concepts else 1.0
            print(f"  关键词覆盖率：{covered_count}/{len(concepts)} = {result.coverage_score:.0%}")

        results.append(result)

    return results


def judge_with_llm(query: str, context: str, concepts: list[str]) -> list[dict]:
    """用 SEA-LION 评估检索上下文覆盖了哪些 required concepts。"""
    try:
        from chatbot.utils.llm_factory import call_sealion
        concepts_str = "\n".join(f"- {c}" for c in concepts)
        prompt = _JUDGE_PROMPT.format(
            query    = query,
            context  = context[:2000],   # 限长防 token 超限
            concepts = concepts_str,
        )
        raw = call_sealion("You are a precise JSON-only evaluator.", prompt, reasoning=False)
        raw = raw.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
        return data.get("results", [])
    except Exception as e:
        print(f"  [Judge] LLM 裁判失败：{e}")
        return []


def print_summary(results: list[EvalResult]) -> None:
    total     = len(results)
    oos_cases = [r for r in results if r.expect_empty]
    med_cases = [r for r in results if not r.expect_empty]

    oos_pass  = sum(1 for r in oos_cases if r.coverage_score == 1.0)
    med_valid = [r for r in med_cases if r.coverage_score >= 0]

    print(f"\n{'='*60}")
    print(f"评测结果汇总：{total} 个用例")
    print(f"  超出范围保护：{oos_pass}/{len(oos_cases)} 正确返回空")

    if med_valid:
        avg_coverage = sum(r.coverage_score for r in med_valid) / len(med_valid)
        above_80     = sum(1 for r in med_valid if r.coverage_score >= 0.8)
        empty_fail   = sum(1 for r in med_cases if r.is_empty)
        print(f"  平均概念覆盖率：{avg_coverage:.1%}")
        print(f"  覆盖率 ≥ 80%：{above_80}/{len(med_valid)} 个用例")
        print(f"  检索失败（空返回）：{empty_fail} 个")

    # 按语言分组
    print(f"\n按语言：")
    for lang in ["English", "Chinese", "Malay", "Tamil"]:
        lang_cases = [r for r in med_valid if r.lang == lang]
        if lang_cases:
            avg = sum(r.coverage_score for r in lang_cases) / len(lang_cases)
            print(f"  {lang:10s}：{avg:.1%}（{len(lang_cases)} 个用例）")

    # 按类别分组
    print(f"\n按类别：")
    categories = sorted(set(r.category for r in med_valid))
    for cat in categories:
        cat_cases = [r for r in med_valid if r.category == cat]
        avg = sum(r.coverage_score for r in cat_cases) / len(cat_cases)
        print(f"  {cat:15s}：{avg:.1%}（{len(cat_cases)} 个用例）")

    # 低覆盖率用例
    low = [r for r in med_valid if r.coverage_score < 0.6 and not r.error]
    if low:
        print(f"\n低覆盖率用例（< 60%）：")
        for r in sorted(low, key=lambda x: x.coverage_score):
            print(f"  [{r.case_id}] {r.coverage_score:.0%} — {r.query[:50]}")

    # 错误用例
    errors = [r for r in results if r.error]
    if errors:
        print(f"\n异常用例：")
        for r in errors:
            print(f"  [{r.case_id}] {r.error}")


def save_results(results: list[EvalResult]) -> None:
    data = [
        {
            "id":             r.case_id,
            "query":          r.query,
            "lang":           r.lang,
            "category":       r.category,
            "coverage_score": r.coverage_score,
            "is_empty":       r.is_empty,
            "expect_empty":   r.expect_empty,
            "concept_results": r.concept_results,
            "context_preview": r.context[:200] if r.context else "",
            "error":          r.error,
        }
        for r in results
    ]
    RESULTS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n结果已保存：{RESULTS_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RAG 独立评测")
    parser.add_argument("--type",     choices=["single", "multi"], help="只跑单轮或多轮")
    parser.add_argument("--category", help="只跑某个类别（medication/food/exercise/...）")
    parser.add_argument("--no-llm",  action="store_true", help="跳过 LLM 裁判，用关键词覆盖率")
    parser.add_argument("--limit",   type=int, default=0, help="限制用例数量（调试用）")
    args = parser.parse_args()

    cases = load_dataset()

    if args.type:
        cases = [c for c in cases if c.get("type") == args.type]
    if args.category:
        cases = [c for c in cases if c.get("category") == args.category]
    if args.limit:
        cases = cases[:args.limit]

    print(f"开始评测：{len(cases)} 个用例，LLM裁判={'开启' if not args.no_llm else '关闭'}")

    results = run_eval(cases, use_llm=not args.no_llm)
    print_summary(results)
    save_results(results)
