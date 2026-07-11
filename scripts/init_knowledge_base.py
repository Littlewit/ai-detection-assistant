"""知识库初始化脚本 - 按10大检测类别分区构建"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import STANDARDS_DIR, STANDARD_CATEGORIES
from app.services.knowledge_base import add_documents_to_kb


def scan_documents(directory: str) -> list:
    """扫描目录下的文档文件"""
    from langchain_community.document_loaders import TextLoader
    docs = []
    if not os.path.isdir(directory):
        return docs

    for root, _, files in os.walk(directory):
        for f in files:
            filepath = os.path.join(root, f)
            ext = os.path.splitext(f)[1].lower()
            if ext == ".txt":
                try:
                    loader = TextLoader(filepath, encoding="utf-8")
                    loaded = loader.load()
                    for doc in loaded:
                        doc.metadata["source"] = filepath
                        doc.metadata["filename"] = f
                    docs.extend(loaded)
                except Exception as e:
                    print(f"  [跳过] {filepath}: {e}")
    return docs


def main():
    print("=" * 60)
    print("AI检测助手 - 知识库初始化")
    print("=" * 60)

    total_chunks = 0

    for category, description in STANDARD_CATEGORIES.items():
        category_dir = os.path.join(STANDARDS_DIR, category)
        print(f"\n[{category}] {description}")
        print(f"  目录: {category_dir}")

        docs = scan_documents(category_dir)
        if not docs:
            print("  (目录为空，跳过)")
            continue

        print(f"  加载 {len(docs)} 个文档...")
        chunks = add_documents_to_kb(docs, category)
        total_chunks += chunks
        print(f"  完成: 生成 {chunks} 个文档块")

    print(f"\n{'=' * 60}")
    print(f"初始化完成! 共生成 {total_chunks} 个文档块")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
