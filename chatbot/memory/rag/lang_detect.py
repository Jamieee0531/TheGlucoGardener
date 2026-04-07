from __future__ import annotations
"""
语言检测模块
============
支持新加坡四种常用语言：英语 / 中文 / 马来语 / 泰米尔语
返回标准化语言代码，供 RAG 检索和 Agent prompt 使用。
"""

# langdetect 代码 → 标准化代码
_NORMALIZE: dict[str, str] = {
    "zh-cn": "zh",
    "zh-tw": "zh",
    "zh":    "zh",
    "en":    "en",
    "ms":    "ms",
    "ta":    "ta",
}

_SUPPORTED = {"en", "zh", "ms", "ta"}

# 语言代码 → prompt 用的语言名称（与 users.language 字段值一致）
LANG_NAME: dict[str, str] = {
    "en": "English",
    "zh": "Chinese",
    "ms": "Malay",
    "ta": "Tamil",
}

# 反向映射：users.language 字段值 → 语言代码（供 retriever Tamil 检索判断用）
LANG_CODE: dict[str, str] = {v: k for k, v in LANG_NAME.items()}

# 高频马来语词（不与英语重叠），命中 2+ 个即判定为马来语
_MALAY_MARKERS = {
    "saya", "anda", "dengan", "yang", "untuk", "tidak", "ada", "ini",
    "itu", "atau", "pada", "akan", "boleh", "sudah", "buat", "darah",
    "gula", "paras", "harus", "apa", "bagaimana", "kenapa", "bila",
    "mana", "ubat", "sakit", "doktor", "hospital", "makanan", "makan",
    "minuman", "tekanan", "pesakit", "rawatan", "penyakit", "berasa",
}


def detect_lang(text: str) -> str:
    """
    检测文本语言，返回 en | zh | ms | ta。
    无法识别或不在支持列表内时，降级返回 en。

    检测顺序：
      1. 中文字符比例（快速，规避 langdetect 随机性）
      2. 马来语关键词命中（langdetect 对拉丁语系区分度差）
      3. langdetect（覆盖 Tamil 及其余语言）
    """
    if not text or not text.strip():
        return "en"

    # 1. 中文
    chinese_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    if chinese_chars > len(text) * 0.2:
        return "zh"

    # 2. 马来语关键词（≥2 个高频词命中）
    words = set(text.lower().split())
    if len(words & _MALAY_MARKERS) >= 2:
        return "ms"

    # 3. langdetect
    try:
        from langdetect import detect, DetectorFactory
        DetectorFactory.seed = 0          # 固定随机种子，结果稳定
        raw  = detect(text)
        lang = _NORMALIZE.get(raw, raw)
        return lang if lang in _SUPPORTED else "en"
    except Exception:
        return "en"
