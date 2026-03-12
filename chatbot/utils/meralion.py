"""
utils/meralion.py
MERaLiON API 集成
流程：上传音频 → /transcribe → /analyze → 解析情绪标签
"""
import os
import re
import time
import requests
from dotenv import load_dotenv

load_dotenv()

MERALION_BASE_URL = os.getenv("MERALION_BASE_URL", "https://api.cr8lab.com")
MERALION_API_KEY  = os.getenv("MERALION_API_KEY", "")

# /analyze返回的emotion词 → 我们的标签体系
EMOTION_KEYWORD_MAP = {
    # sad
    "sad": "sad", "unhappy": "sad", "depressed": "sad",
    "disappointed": "sad", "grief": "sad", "melancholy": "sad",
    "lonely": "sad", "sorrowful": "sad",
    # anxious
    "anxious": "anxious", "worried": "anxious", "nervous": "anxious",
    "fearful": "anxious", "scared": "anxious", "stressed": "anxious",
    "tense": "anxious", "apprehensive": "anxious",
    # angry
    "angry": "angry", "frustrated": "angry", "irritated": "angry",
    "annoyed": "angry", "furious": "angry", "agitated": "angry",
    "hostile": "angry",
    # happy
    "happy": "happy", "joyful": "happy", "excited": "happy",
    "pleased": "happy", "content": "happy", "cheerful": "happy",
    "positive": "happy", "enthusiastic": "happy",
    # confused
    "confused": "confused", "uncertain": "confused", "puzzled": "confused",
    "hesitant": "confused",
    # neutral
    "neutral": "neutral", "calm": "neutral", "flat": "neutral",
}


def _upload_audio(audio_path: str) -> str:
    """上传音频到S3，返回fileKey"""
    filename    = os.path.basename(audio_path)
    file_size   = os.path.getsize(audio_path)
    content_type = "audio/wav" if filename.endswith(".wav") else "audio/mpeg"

    # Step1: 获取presigned URL
    resp = requests.post(
        f"{MERALION_BASE_URL}/upload-url",
        headers={"x-api-key": MERALION_API_KEY, "Content-Type": "application/json"},
        json={"filename": filename, "contentType": content_type, "fileSize": file_size},
        timeout=15,
    )
    resp.raise_for_status()
    data       = resp.json()["response"]
    upload_url = data["url"]
    file_key   = data["key"]

    # Step2: PUT上传音频
    with open(audio_path, "rb") as f:
        put_resp = requests.put(
            upload_url,
            headers={"Content-Type": content_type},
            data=f,
            timeout=60,
        )
    put_resp.raise_for_status()
    print(f"[MERaLiON] 音频上传成功：{filename}")
    return file_key


def _transcribe(file_key: str) -> str:
    """调用/transcribe，返回转录文字"""
    resp = requests.post(
        f"{MERALION_BASE_URL}/transcribe",
        headers={"x-api-key": MERALION_API_KEY, "Content-Type": "application/json"},
        json={"key": file_key},
        timeout=60,
    )
    resp.raise_for_status()
    text = resp.json()["response"]["text"]
    print(f"[MERaLiON] 转录完成：{text[:50]}...")
    return text


def _analyze(file_key: str) -> tuple[str, float]:
    """
    调用/analyze，解析情绪标签
    返回 (emotion_label, confidence)
    """
    resp = requests.post(
        f"{MERALION_BASE_URL}/analyze",
        headers={"x-api-key": MERALION_API_KEY, "Content-Type": "application/json"},
        json={"key": file_key, "segment_length": 4},
        timeout=60,
    )
    resp.raise_for_status()
    raw_text = resp.json()["response"]["text"].lower()

    # 从文字描述里提取emotion关键词
    # 格式例：Emotion: Frustrated Tone: Critical ...
    emotion_label = "neutral"
    matched_word  = None

    # 优先匹配"Emotion:"后面的词
    emotion_match = re.search(r"emotion[:\s]+(\w+)", raw_text)
    if emotion_match:
        word = emotion_match.group(1).strip()
        emotion_label = EMOTION_KEYWORD_MAP.get(word, "neutral")
        matched_word  = word

    # 如果没匹配到，扫描全文
    if emotion_label == "neutral" and not matched_word:
        for keyword, label in EMOTION_KEYWORD_MAP.items():
            if keyword in raw_text:
                emotion_label = label
                matched_word  = keyword
                break

    # MERaLiON没有置信度，根据是否明确匹配给固定值
    confidence = 0.8 if matched_word and matched_word != "neutral" else 0.5

    print(f"[MERaLiON] 情绪分析：原始='{raw_text.strip()}' → 标签={emotion_label}（置信度{confidence}）")
    return emotion_label, confidence


def process_voice_input(audio_path: str) -> dict:
    """
    主入口：音频文件路径 → 转录文字 + 情绪标签
    返回格式与ChatState兼容
    """
    try:
        file_key          = _upload_audio(audio_path)
        time.sleep(1)  # 等待S3处理完成
        transcribed_text  = _transcribe(file_key)
        emotion_label, confidence = _analyze(file_key)

        return {
            "transcribed_text":   transcribed_text,
            "emotion_label":      emotion_label,
            "emotion_confidence": confidence,
        }

    except Exception as e:
        print(f"[MERaLiON] 调用失败：{e}，返回默认值")
        return {
            "transcribed_text":   "",
            "emotion_label":      "neutral",
            "emotion_confidence": 0.0,
        }


# ── Mock模式（无API Key时使用）────────────────────────────
def process_voice_input_mock(audio_path: str) -> dict:
    """测试用mock，不调用真实API"""
    print(f"[MERaLiON Mock] 处理：{audio_path}")
    return {
        "transcribed_text":   "我今天血糖有点高，很担心",
        "emotion_label":      "anxious",
        "emotion_confidence": 0.82,
    }
