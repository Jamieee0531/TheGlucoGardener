"""
PDF 文档解析器
==============
将 raw_docs/ 下的 PDF 文件解析为干净文本，写入 knowledge/ 目录，
供 loader.py 后续切块入向量库。

两条解析路径：
  - pymupdf（fitz）：8 个文字型 PDF → knowledge/{stem}.txt
  - camelot         ：ktph_gi_table.pdf → knowledge/gi_table.json

用法：
  python -m chatbot.memory.rag.pdf_parser          # 解析全部
  python -m chatbot.memory.rag.pdf_parser --force  # 强制重新解析（覆盖已有 txt）
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

RAW_DOCS_DIR  = Path(__file__).parent / "raw_docs"
KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"

# ktph_gi_table.pdf 同样走 pymupdf → txt → 向量库
# 三列合并表头布局，camelot 无法可靠解析，改走普通文本路径
GI_TABLE_PDF  = "ktph_gi_table.pdf"   # 保留常量供 parse_all 识别，不再特殊处理
GI_TABLE_JSON = KNOWLEDGE_DIR / "gi_table.json"   # 旧 JSON，保留向后兼容


# ── 文本清洗 ──────────────────────────────────────────────────────────

# 常见页眉 / 页脚噪音模式
_NOISE_PATTERNS = [
    re.compile(r"page\s+\d+\s+of\s+\d+", re.I),   # "Page 1 of 10"
    re.compile(r"^\s*-\s*\d+\s*-\s*$", re.M),      # "- 1 -"
    re.compile(r"^\s*\d+\s*$", re.M),               # 单独一行的页码
    re.compile(r"\ufffd"),                           # Unicode 替换字符（乱码）
]


def _clean_text(raw: str) -> str:
    """移除页码、乱码、多余空白，规范化段落间距。"""
    text = raw
    for pat in _NOISE_PATTERNS:
        text = pat.sub("", text)

    # 合并多余空行（3+ 个换行 → 2 个）
    text = re.sub(r"\n{3,}", "\n\n", text)
    # 移除行首尾空白
    lines = [line.rstrip() for line in text.splitlines()]
    text  = "\n".join(lines)
    # 修复断字（"medica-\ntion" → "medication"）
    text = re.sub(r"-\n(\S)", r"\1", text)

    return text.strip()


# ── pymupdf 解析 ──────────────────────────────────────────────────────

def parse_pdf_text(pdf_path: Path) -> str:
    """
    提取 PDF 文本。
    优先用 pymupdf 读取内嵌文本层（快，无损）；
    若整个文档提取为空（扫描件），自动降级为 pytesseract OCR。
    """
    try:
        import fitz  # pymupdf
    except ImportError:
        raise ImportError("请先安装：pip install pymupdf")

    doc   = fitz.open(str(pdf_path))
    pages = []
    for page in doc:
        page_text = page.get_text("text")   # 按阅读顺序提取文本流
        if page_text.strip():
            pages.append(page_text)
    doc.close()

    if pages:
        return _clean_text("\n\n".join(pages))

    # ── 降级：OCR（扫描件）────────────────────────────────────────
    print(f"[Parser]   → 无文本层，切换 OCR 模式：{pdf_path.name}")
    return _ocr_pdf(pdf_path)


def _ocr_pdf(pdf_path: Path) -> str:
    """
    将 PDF 每页渲染为图片，用 pytesseract 做 OCR，返回合并文本。
    需要系统安装 tesseract-ocr 和 poppler-utils。
    """
    try:
        from pdf2image import convert_from_path
        import pytesseract
    except ImportError:
        raise ImportError("请先安装：pip install pdf2image pytesseract 及系统 tesseract-ocr")

    images = convert_from_path(str(pdf_path), dpi=300)
    pages  = []
    for img in images:
        text = pytesseract.image_to_string(img, lang="eng")
        if text.strip():
            pages.append(text)
    return _clean_text("\n\n".join(pages))




# ── 主解析流程 ────────────────────────────────────────────────────────

def parse_all(force: bool = False) -> None:
    """
    解析 raw_docs/ 下所有 PDF：
      - ktph_gi_table.pdf → knowledge/gi_table.json
      - 其余 PDF          → knowledge/{stem}.txt
    force=True 时强制覆盖已存在的输出文件。
    """
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(RAW_DOCS_DIR.glob("*.pdf"))
    if not pdf_files:
        print("[Parser] raw_docs/ 目录下没有 PDF 文件")
        return

    for pdf_path in pdf_files:
        # ── 所有 PDF 统一走 pymupdf → txt ────────────────────────
        out_path = KNOWLEDGE_DIR / f"{pdf_path.stem}.txt"
        if out_path.exists() and not force:
            print(f"[Parser] 跳过（已存在）：{out_path.name}")
            continue

        print(f"[Parser] pymupdf 解析：{pdf_path.name}")
        try:
            text = parse_pdf_text(pdf_path)
            if len(text) < 100:
                print(f"[Parser] ✗ {pdf_path.name} 提取文本过短，可能是扫描件")
                continue
            out_path.write_text(text, encoding="utf-8")
            print(f"[Parser] ✓ {out_path.name}（{len(text):,} 字符）")
        except Exception as e:
            print(f"[Parser] ✗ {pdf_path.name} 解析失败：{e}")


# ── 脚本入口 ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="解析 raw_docs/ 下的 PDF 文件")
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="强制重新解析，覆盖已有输出文件",
    )
    args = parser.parse_args()
    parse_all(force=args.force)
    print("[Parser] 全部完成")
