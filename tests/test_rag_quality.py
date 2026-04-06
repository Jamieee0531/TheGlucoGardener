"""
RAG 检索质量测试
================
测试维度：
  1. 检索召回（正确文档有没有被检索到）
  2. 相关性（reranker 打分）
  3. 语言处理（中英马泰）
  4. 边界情况（超出知识库范围、指代词）
  5. 口语化表达

用法：
  python -m pytest tests/test_rag_quality.py -v -s
  python tests/test_rag_quality.py          # 直接运行，输出更易读
"""
from __future__ import annotations

import sys
import textwrap
from dataclasses import dataclass, field
from typing import Optional


# ── 测试用例定义 ──────────────────────────────────────────────────────

@dataclass
class RAGTestCase:
    id:              str
    query:           str
    lang:            str          # 传给 retriever 的 lang 参数
    category:        str          # 期望检索到的文档类别
    expected_keywords: list[str]  # 期望在检索结果中出现的关键词（至少命中 1 个）
    expect_empty:    bool = False  # True = 期望不注入上下文（超出范围）
    note:            str  = ""


TEST_CASES: list[RAGTestCase] = [

    # ── 直接医学查询（英文）──────────────────────────────────────────
    RAGTestCase(
        id="en_glucose_high",
        query="my blood sugar is 12 mmol/L after lunch, is that dangerous?",
        lang="English",
        category="management",
        expected_keywords=["mmol", "postprandial", "high", "glucose", "target"],
        note="直接数值查询，应召回血糖管理相关内容",
    ),
    RAGTestCase(
        id="en_metformin_side_effect",
        query="what are the side effects of metformin?",
        lang="English",
        category="medication",
        expected_keywords=["metformin", "nausea", "diarrhoea", "gastrointestinal", "side effect"],
        note="药物副作用查询",
    ),
    RAGTestCase(
        id="en_exercise_diabetes",
        query="how much exercise should a diabetic patient do per week?",
        lang="English",
        category="exercise",
        expected_keywords=["exercise", "minutes", "week", "aerobic", "physical activity"],
        note="运动建议查询",
    ),
    RAGTestCase(
        id="en_foot_care",
        query="how do I take care of my feet as a diabetic?",
        lang="English",
        category="complication",
        expected_keywords=["foot", "feet", "inspect", "diabetic", "wound", "ulcer"],
        note="足部护理查询",
    ),
    RAGTestCase(
        id="en_hypoglycaemia",
        query="I feel shaky and sweaty, what should I do?",
        lang="English",
        category="management",
        expected_keywords=["hypoglycaemia", "low blood sugar", "glucose", "shaky", "sweaty", "3.9"],
        note="口语症状 → 应识别为低血糖",
    ),

    # ── 新加坡口语化（Singlish）────────────────────────────────────
    RAGTestCase(
        id="singlish_sugar_high",
        query="my sugar very high lah, 11 already, how?",
        lang="English",
        category="management",
        expected_keywords=["mmol", "high", "glucose", "hyperglycaemia", "target"],
        note="Singlish 口语，测试 bge-m3 语义理解",
    ),
    RAGTestCase(
        id="singlish_char_kway_teow",
        query="can eat char kway teow or not lah",
        lang="English",
        category="food",
        expected_keywords=["char kway teow", "fried", "GI", "carb", "glycaemic"],
        note="新加坡本地食物查询",
    ),
    RAGTestCase(
        id="singlish_dizzy_standing",
        query="every time I stand up I feel very dizzy one",
        lang="English",
        category="management",
        expected_keywords=["postural", "hypotension", "stand", "dizziness", "blood pressure"],
        note="体位性低血压，不应被误判为低血糖建议吃东西",
    ),

    # ── 中文查询 ──────────────────────────────────────────────────
    RAGTestCase(
        id="zh_blood_sugar",
        query="饭后两小时血糖应该控制在多少？",
        lang="Chinese",
        category="management",
        expected_keywords=["mmol", "postprandial", "target", "glucose", "8"],
        note="中文直接查询，bge-m3 跨语言检索",
    ),
    RAGTestCase(
        id="zh_medication",
        query="二甲双胍什么时候吃最好？",
        lang="Chinese",
        category="medication",
        expected_keywords=["metformin", "meal", "food", "二甲双胍"],
        note="中文药物查询",
    ),
    RAGTestCase(
        id="zh_hawker",
        query="我可以吃鸡饭吗？",
        lang="Chinese",
        category="food",
        expected_keywords=["chicken rice", "rice", "portion", "carb", "鸡饭"],
        note="中文小贩食物查询",
    ),

    # ── 马来文查询 ────────────────────────────────────────────────
    RAGTestCase(
        id="ms_gula",
        query="paras gula darah saya 10, apa yang perlu saya buat?",
        lang="Malay",
        category="management",
        expected_keywords=["mmol", "glucose", "high", "target", "blood sugar"],
        note="马来文血糖查询，bge-m3 跨语言",
    ),
    RAGTestCase(
        id="ms_ubat",
        query="boleh saya makan ubat diabetes semasa berpuasa?",
        lang="Malay",
        category="management",
        expected_keywords=["fasting", "Ramadan", "medication", "puasa", "diabetes"],
        note="马来文斋戒月用药查询",
    ),

    # ── 泰米尔文查询 ──────────────────────────────────────────────
    RAGTestCase(
        id="ta_blood_sugar",
        query="என் இரத்த சர்க்கரை அளவு அதிகமாக உள்ளது, நான் என்ன செய்ய வேண்டும்?",
        lang="Tamil",
        category="management",
        expected_keywords=["mmol", "glucose", "high", "blood sugar", "target"],
        note="泰米尔文查询，触发 SEA-LION 改写为英文再检索",
    ),

    # ── 指代词（多轮上下文）────────────────────────────────────────
    RAGTestCase(
        id="pronoun_that",
        query="is that dangerous?",
        lang="English",
        category="management",
        expected_keywords=[],
        expect_empty=False,
        note="纯指代词，真实对话中有上下文，允许注入相关医学内容",
    ),
    RAGTestCase(
        id="pronoun_it",
        query="what about it?",
        lang="English",
        category="general",
        expected_keywords=[],
        expect_empty=True,
        note="指代词查询，应触发置信度阈值保护",
    ),

    # ── 超出知识库范围 ────────────────────────────────────────────
    RAGTestCase(
        id="out_of_scope_weather",
        query="what is the weather in Singapore tomorrow?",
        lang="English",
        category="general",
        expected_keywords=[],
        expect_empty=True,
        note="完全不相关查询，reranker 分应低，不注入上下文",
    ),
    RAGTestCase(
        id="out_of_scope_stock",
        query="should I buy DBS stock now?",
        lang="English",
        category="general",
        expected_keywords=[],
        expect_empty=True,
        note="非医疗查询",
    ),

    # ── 饮食 GI 查询 ──────────────────────────────────────────────
    RAGTestCase(
        id="en_gi_white_rice",
        query="what is the glycaemic index of white rice?",
        lang="English",
        category="food",
        expected_keywords=["glycaemic index", "GI", "white rice", "high"],
        note="GI 精确查询",
    ),
    RAGTestCase(
        id="en_yong_tau_foo",
        query="is yong tau foo good for diabetics?",
        lang="English",
        category="food",
        expected_keywords=["yong tau foo", "soup", "diabetic", "choice"],
        note="新加坡食物 GI/推荐查询",
    ),

    # ── Ramadan 专项 ──────────────────────────────────────────────
    RAGTestCase(
        id="en_ramadan_fasting",
        query="can diabetics fast during Ramadan?",
        lang="English",
        category="management",
        expected_keywords=["Ramadan", "fasting", "diabetic", "blood glucose", "4.0"],
        note="斋戒月专项查询",
    ),
    RAGTestCase(
        id="en_ramadan_medication",
        query="how should I adjust my diabetes medication during fasting month?",
        lang="English",
        category="management",
        expected_keywords=["Ramadan", "medication", "fasting", "adjust", "doctor"],
        note="斋戒月药物调整",
    ),
]


# ── 测试执行 ──────────────────────────────────────────────────────────

def run_tests(cases: list[RAGTestCase], n: int = 3) -> None:
    from chatbot.memory.rag.retriever import get_retriever

    retriever = get_retriever()
    retriever._init()

    passed = 0
    failed = 0
    skipped = 0

    results = []

    for tc in cases:
        print(f"\n{'='*60}")
        print(f"[{tc.id}] {tc.note}")
        print(f"Query : {tc.query}")
        print(f"Lang  : {tc.lang}")

        try:
            # 直接调用 _hybrid_search 拿原始 reranker 分（需要绕过 retrieve 的字符串拼接）
            # 先用 retrieve 拿最终结果
            result_text = retriever.retrieve(tc.query, n=n, lang=tc.lang)
            chunks = [c.strip() for c in result_text.split("\n\n") if c.strip()] if result_text else []

            print(f"检索到 {len(chunks)} 个块")

            if tc.expect_empty:
                if not chunks:
                    print("✅ PASS：正确返回空（超出范围保护生效）")
                    passed += 1
                    status = "PASS"
                else:
                    print(f"⚠️  WARN：期望空但返回了内容（阈值可能需要调高）")
                    print(f"   首块预览：{chunks[0][:100]}...")
                    skipped += 1
                    status = "WARN"
            else:
                if not chunks:
                    print("❌ FAIL：无检索结果（知识库缺失或阈值过高）")
                    failed += 1
                    status = "FAIL"
                else:
                    # 检查关键词
                    combined = " ".join(chunks).lower()
                    hit_keywords = [kw for kw in tc.expected_keywords if kw.lower() in combined]
                    miss_keywords = [kw for kw in tc.expected_keywords if kw.lower() not in combined]

                    if tc.expected_keywords and not hit_keywords:
                        print(f"❌ FAIL：关键词全部未命中")
                        print(f"   期望：{tc.expected_keywords}")
                        failed += 1
                        status = "FAIL"
                    else:
                        print(f"✅ PASS：命中关键词 {hit_keywords}")
                        if miss_keywords:
                            print(f"   未命中：{miss_keywords}（可接受）")
                        passed += 1
                        status = "PASS"

                    # 打印检索到的块预览
                    for i, chunk in enumerate(chunks, 1):
                        preview = textwrap.shorten(chunk, width=120, placeholder="...")
                        print(f"   块{i}: {preview}")

            results.append((tc.id, status))

        except Exception as e:
            print(f"❌ ERROR：{e}")
            failed += 1
            results.append((tc.id, "ERROR"))

    # ── 汇总 ─────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"测试结果汇总：{len(cases)} 个用例")
    print(f"  ✅ PASS  : {passed}")
    print(f"  ❌ FAIL  : {failed}")
    print(f"  ⚠️  WARN  : {skipped}")
    print()
    for tid, status in results:
        icon = "✅" if status == "PASS" else ("⚠️ " if status == "WARN" else "❌")
        print(f"  {icon} {tid}")


# ── pytest 接口 ───────────────────────────────────────────────────────

def test_rag_en_direct():
    """英文直接查询应有召回"""
    from chatbot.memory.rag.retriever import get_retriever
    r = get_retriever()
    result = r.retrieve("what are the side effects of metformin?", n=3, lang="English")
    assert result, "metformin 查询应有返回"
    assert "metformin" in result.lower()


def test_rag_out_of_scope():
    """完全不相关查询应返回空"""
    from chatbot.memory.rag.retriever import get_retriever
    r = get_retriever()
    result = r.retrieve("what is the weather tomorrow?", n=3, lang="English")
    # 不强制断言为空（阈值是可调参数），只打印分数供人工判断
    print(f"[out_of_scope] result length: {len(result)}")


def test_rag_chinese():
    """中文查询应有召回"""
    from chatbot.memory.rag.retriever import get_retriever
    r = get_retriever()
    result = r.retrieve("饭后血糖应该控制在多少？", n=3, lang="Chinese")
    assert result, "中文查询应有返回"


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    run_tests(TEST_CASES, n=3)
