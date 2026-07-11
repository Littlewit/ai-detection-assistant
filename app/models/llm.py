"""千问大模型初始化与管理"""

import os
from langchain_community.chat_models import ChatTongyi
from langchain_community.embeddings import DashScopeEmbeddings
from app.config import get_settings


def get_text_llm() -> ChatTongyi:
    """获取千问文本模型"""
    settings = get_settings()
    os.environ["DASHSCOPE_API_KEY"] = settings.dashscope_api_key
    return ChatTongyi(
        model=settings.qwen_text_model,
        dashscope_api_key=settings.dashscope_api_key,
    )


def get_vl_llm() -> ChatTongyi:
    """获取千问多模态视觉模型"""
    settings = get_settings()
    os.environ["DASHSCOPE_API_KEY"] = settings.dashscope_api_key
    return ChatTongyi(
        model=settings.qwen_vl_model,
        dashscope_api_key=settings.dashscope_api_key,
    )


def get_embeddings() -> DashScopeEmbeddings:
    """获取千问 Embedding 模型"""
    settings = get_settings()
    os.environ["DASHSCOPE_API_KEY"] = settings.dashscope_api_key
    return DashScopeEmbeddings(
        model=settings.qwen_embedding_model,
        dashscope_api_key=settings.dashscope_api_key,
    )
