"""
tests/check_emotion_confidence.py
检查 MERaLiON 对特定消息的情绪识别置信度

运行：cd TheGlucoGardener && python -m tests.check_emotion_confidence
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from chatbot.utils.meralion import process_text_input

CASES = [
    # Hybrid 失败用例
    ("H1", "I'm feeling really down today, my daughter hasn't called. Also my blood sugar has been high all week."),
    ("H2", "I'm so stressed and anxious, I don't know if I'm taking my medication correctly."),
    ("H3", "Managing diabetes alone is so tiring, and I keep forgetting to eat on time."),
    ("H4", "I feel scared every time I check my blood sugar because the numbers are always too high."),
    ("S3", "I have a small cut on my foot that's not healing well."),
    ("S4", "I've been feeling very tired lately even after sleeping well."),
    # 对照组：正确检出的
    ("C1", "I feel so lonely living alone, my daughter is far away in Australia."),
    ("CR1", "I feel like giving up on my treatment, what's the point anymore."),
    ("C3", "I'm so tired of watching what I eat every single day."),
]

print(f"\n{'ID':<5} {'情绪':<10} {'置信度':<8} 输入")
print("-" * 80)
for id_, text in CASES:
    result = process_text_input(text)
    label  = result["emotion_label"]
    conf   = result["emotion_confidence"]
    flag   = "⚠️" if label == "neutral" and id_.startswith("H") else ""
    print(f"{id_:<5} {label:<10} {conf:<8.3f} {flag} {text[:55]}...")
