"""知识库管理服务 - 10大检测类别分区向量检索"""

import os
from typing import Optional
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.models.llm import get_embeddings
from app.config import get_settings, STANDARDS_DIR

# 文档切分器（针对检测标准文档特点优化）
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    separators=["\n\n", "\n", "。", "；", "条款", "章节"],
)


def get_vectorstore(category: str = "all") -> Chroma:
    """获取指定类别的向量存储"""
    settings = get_settings()
    embeddings = get_embeddings()
    persist_dir = os.path.join(settings.chroma_persist_dir, category)
    os.makedirs(persist_dir, exist_ok=True)

    try:
        return Chroma(
            collection_name=f"standards_{category}",
            embedding_function=embeddings,
            persist_directory=persist_dir,
        )
    except Exception:
        return Chroma(
            collection_name=f"standards_{category}",
            embedding_function=embeddings,
            persist_directory=persist_dir,
        )


def add_documents_to_kb(documents: list, category: str = "all") -> int:
    """向知识库添加文档"""
    splits = text_splitter.split_documents(documents)
    vectorstore = get_vectorstore(category)
    vectorstore.add_documents(splits)
    return len(splits)


def search_knowledge(query: str, category: str = "all", k: int = 8) -> list:
    """检索知识库"""
    vectorstore = get_vectorstore(category)
    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={"k": k, "fetch_k": k * 3},
    )
    try:
        return retriever.invoke(query)
    except Exception:
        return []
