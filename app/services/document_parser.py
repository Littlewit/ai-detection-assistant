"""文档解析服务 - 申请表/拆分表/报告"""

import os
import pandas as pd
from typing import Optional


def parse_application_form(file_path: str) -> dict:
    """解析产品申请表"""
    ext = os.path.splitext(file_path)[1].lower()
    if ext in (".xlsx", ".xls"):
        df = pd.read_excel(file_path)
    elif ext == ".csv":
        df = pd.read_csv(file_path)
    else:
        raise ValueError(f"不支持的申请表格式: {ext}")
    return {"rows": df.to_dict(orient="records"), "columns": list(df.columns)}


def parse_split_table(file_path: str) -> dict:
    """解析样板拆分表"""
    ext = os.path.splitext(file_path)[1].lower()
    if ext in (".xlsx", ".xls"):
        df = pd.read_excel(file_path)
    elif ext == ".csv":
        df = pd.read_csv(file_path)
    else:
        raise ValueError(f"不支持的拆分表格式: {ext}")
    return {"rows": df.to_dict(orient="records"), "columns": list(df.columns)}


def parse_report(file_path: str) -> str:
    """解析检测报告（支持 PDF / Word）"""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        from PyPDF2 import PdfReader
        reader = PdfReader(file_path)
        text_parts = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                text_parts.append(f"[第{i+1}页]\n{text}")
        return "\n\n".join(text_parts)
    elif ext == ".docx":
        from docx import Document
        doc = Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    elif ext == ".txt":
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    else:
        raise ValueError(f"不支持的报告格式: {ext}")


def parse_table_to_text(table_data: dict) -> str:
    """将表格数据转为可读文本"""
    rows = table_data.get("rows", [])
    if not rows:
        return "（空表格）"
    lines = []
    for i, row in enumerate(rows):
        parts = [f"{k}: {v}" for k, v in row.items() if v is not None]
        lines.append(f"第{i+1}行: {'; '.join(parts)}")
    return "\n".join(lines)
