"""
tests/run_mdm_chen_tests.py
Mdm Chen 测试集自动化运行器

运行方式：
    cd TheGlucoGardener
    python -m tests.run_mdm_chen_tests
"""
import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# ── 测试用例 ──────────────────────────────────────────────────────────
TEST_CASES = [
    # 模块一：食物咨询
    {"id": "F1", "category": "食物咨询", "input": "Is char kway teow ok for me to eat?",                                     "expected_intent": "medical"},
    {"id": "F2", "category": "食物咨询", "input": "Can I eat nasi lemak for breakfast?",                                     "expected_intent": "medical"},
    {"id": "F3", "category": "食物咨询", "input": "What about roti prata, is it high GI?",                                   "expected_intent": "medical"},
    {"id": "F4", "category": "食物咨询", "input": "I had wonton noodles for dinner tonight, will my blood sugar spike?",     "expected_intent": "medical"},
    {"id": "F5", "category": "食物咨询", "input": "Is brown rice better than white rice for diabetes?",                      "expected_intent": "medical"},

    # 模块二：血糖数据
    {"id": "G1", "category": "血糖数据", "input": "My glucose reading is 9.5 after lunch, is that normal?",                  "expected_intent": "medical"},
    {"id": "G2", "category": "血糖数据", "input": "What has my blood sugar been like this week?",                            "expected_intent": "medical"},
    {"id": "G3", "category": "血糖数据", "input": "Why does my sugar always go high after dinner?",                          "expected_intent": "medical"},
    {"id": "G4", "category": "血糖数据", "input": "My reading was 4.1 this morning, should I be worried?",                   "expected_intent": "medical"},

    # 模块三：药物管理
    {"id": "M1", "category": "药物管理", "input": "I forgot to take my Metformin this morning, what should I do?",           "expected_intent": "medical"},
    {"id": "M2", "category": "药物管理", "input": "Metformin is making me feel nauseous, is that normal?",                   "expected_intent": "medical"},
    {"id": "M3", "category": "药物管理", "input": "Can I take Metformin with my blood pressure medicine?",                   "expected_intent": "medical"},
    {"id": "M4", "category": "药物管理", "input": "Should I take Metformin before or after meals?",                          "expected_intent": "medical"},

    # 模块四：Hybrid
    {"id": "H1", "category": "Hybrid",   "input": "I'm feeling really down today, my daughter hasn't called. Also my blood sugar has been high all week.", "expected_intent": "hybrid"},
    {"id": "H2", "category": "Hybrid",   "input": "I'm so stressed and anxious, I don't know if I'm taking my medication correctly.",                      "expected_intent": "hybrid"},
    {"id": "H3", "category": "Hybrid",   "input": "Managing diabetes alone is so tiring, and I keep forgetting to eat on time.",                           "expected_intent": "hybrid"},
    {"id": "H4", "category": "Hybrid",   "input": "I feel scared every time I check my blood sugar because the numbers are always too high.",              "expected_intent": "hybrid"},

    # 模块五：情绪陪伴
    {"id": "C1", "category": "情绪陪伴", "input": "I feel so lonely living alone, my daughter is far away in Australia.",   "expected_intent": "companion"},
    {"id": "C2", "category": "情绪陪伴", "input": "Good morning! I just came back from my walk, feeling good today.",       "expected_intent": "companion"},
    {"id": "C3", "category": "情绪陪伴", "input": "I'm so tired of watching what I eat every single day.",                  "expected_intent": "companion"},
    {"id": "C4", "category": "情绪陪伴", "input": "Thank you for always being here for me.",                                "expected_intent": "companion"},

    # 模块六：并发症
    {"id": "S1", "category": "并发症",   "input": "I feel dizzy every time I stand up after sitting. Is this low blood sugar?",      "expected_intent": "medical"},
    {"id": "S2", "category": "并发症",   "input": "My feet feel numb and tingly sometimes, is that related to diabetes?",            "expected_intent": "medical"},
    {"id": "S3", "category": "并发症",   "input": "I have a small cut on my foot that's not healing well.",                          "expected_intent": "medical"},
    {"id": "S4", "category": "并发症",   "input": "I've been feeling very tired lately even after sleeping well.",                    "expected_intent": "medical"},

    # 模块七：运动建议
    {"id": "E1", "category": "运动建议", "input": "Is it safe to exercise when my blood sugar is 12?",                               "expected_intent": "medical"},
    {"id": "E2", "category": "运动建议", "input": "What kind of exercise is best for a 68-year-old diabetic?",                       "expected_intent": "medical"},
    {"id": "E3", "category": "运动建议", "input": "My glucose dropped to 4.2 during my morning walk, what should I do?",             "expected_intent": "medical"},

    # 模块八：危机
    {"id": "CR1", "category": "危机",    "input": "I feel like giving up on my treatment, what's the point anymore.",               "expected_intent": "crisis"},
    {"id": "CR2", "category": "危机",    "input": "Sometimes I wonder if it would be easier to just stop taking my medication.",     "expected_intent": "crisis"},

    # 模块九：本地资源
    {"id": "L1", "category": "本地资源", "input": "What is CHAS and can I use it for my diabetes checkup?",                         "expected_intent": "medical"},
    {"id": "L2", "category": "本地资源", "input": "Where can I do a free health screening in Singapore?",                           "expected_intent": "medical"},
]


def _per_turn(user_input: str, user_id: str) -> dict:
    return {
        "user_id":            user_id,
        "user_input":         user_input,
        "input_mode":         "text",
        "chat_mode":          "personal",
        "audio_path":         None,
        "transcribed_text":   None,
        "emotion_label":      "neutral",
        "emotion_confidence": 0.0,
        "emotion_intensity":  None,
        "intent":             None,
        "all_intents":        None,
        "response":           None,
        "emotion_log":        None,
        "image_paths":        None,
        "vision_result":      None,
    }


def run_all():
    from chatbot.graph.builder import app
    from chatbot.utils.memory import get_user_profile

    user_id = "user_001"
    config  = {"configurable": {"thread_id": f"test_{int(time.time())}"}}

    app.update_state(config, {
        "user_profile": get_user_profile(user_id),
        "history":      [],
    })

    results = []
    total = len(TEST_CASES)

    print(f"\n{'='*60}")
    print(f"  Mdm Chen 测试集  ({total} 个用例)")
    print(f"{'='*60}\n")

    for i, tc in enumerate(TEST_CASES, 1):
        print(f"[{i:02d}/{total}] {tc['id']} — {tc['input'][:60]}...")
        t0 = time.time()
        try:
            result  = app.invoke(_per_turn(tc["input"], user_id), config=config)
            elapsed = round(time.time() - t0, 1)

            actual_intent     = result.get("intent", "?")
            actual_emotion    = result.get("emotion_label", "?")
            emotion_intensity = result.get("emotion_intensity") or "-"
            response          = result.get("response", "")

            intent_ok = actual_intent == tc["expected_intent"]
            status    = "✅" if intent_ok else "⚠️"

            print(f"  {status} intent={actual_intent} emotion={actual_emotion}({emotion_intensity}) ({elapsed}s)")

            results.append({
                **tc,
                "actual_intent":     actual_intent,
                "actual_emotion":    actual_emotion,
                "emotion_intensity": emotion_intensity,
                "response":          response,
                "elapsed":           elapsed,
                "status":            status,
            })
        except Exception as e:
            elapsed = round(time.time() - t0, 1)
            print(f"  ❌ ERROR: {e}")
            results.append({
                **tc,
                "actual_intent":     "ERROR",
                "actual_emotion":    "ERROR",
                "emotion_intensity": "ERROR",
                "response":          str(e),
                "elapsed":           elapsed,
                "status":            "❌",
            })

    return results


def write_results_md(results: list):
    now     = datetime.now().strftime("%Y-%m-%d %H:%M")
    passed  = sum(1 for r in results if r["status"] == "✅")
    warned  = sum(1 for r in results if r["status"] == "⚠️")
    failed  = sum(1 for r in results if r["status"] == "❌")
    total   = len(results)
    avg_t   = round(sum(r["elapsed"] for r in results) / total, 1)

    lines = [
        "# Mdm Chen 测试结果\n",
        f"**运行时间**：{now}  ",
        f"**用例总数**：{total}  ",
        f"**通过**：{passed} ✅  **路由偏差**：{warned} ⚠️  **错误**：{failed} ❌  ",
        f"**平均响应时间**：{avg_t}s\n",
        "---\n",
    ]

    # 按 category 分组
    categories = {}
    for r in results:
        categories.setdefault(r["category"], []).append(r)

    for cat, items in categories.items():
        lines.append(f"## {cat}\n")
        for r in items:
            intent_match = "✅" if r["actual_intent"] == r["expected_intent"] else "⚠️"

            lines += [
                f"### {r['id']} {r['status']}",
                f"**输入**：{r['input']}  ",
                f"**情绪**：{r['actual_emotion']} ({r.get('emotion_intensity', '-')})  ",
                f"**Intent**：{r['actual_intent']} {intent_match}（预期：{r['expected_intent']}）  ",
                f"**耗时**：{r['elapsed']}s  ",
                f"\n**回复**：\n> {r['response']}\n",
                "---\n",
            ]

    return "\n".join(lines), passed, total, avg_t


def save_results(content: str, filename: str):
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    return out_path


if __name__ == "__main__":
    results = run_all()
    content, passed, total, avg_t = write_results_md(results)
    path = save_results(content, "mdm_chen_results.md")
    print(f"\n结果已写入：{path}")
    print(f"通过 {passed}/{total}  |  平均 {avg_t}s/条")
