"""智能问答 LangGraph Agent - RAG 增强"""

import json
import asyncio
from typing import AsyncGenerator
from langchain_core.prompts import ChatPromptTemplate
from dashscope import Generation
from app.models.llm import get_text_llm
from app.config import get_settings
from app.services.knowledge_base import search_knowledge



QA_PROMPT = """你是一名资深检测工程师，拥有 CNAS/CMA/CPSC 等资质。
请根据以下检索到的标准文件、历史报告和公司内部规范，回答用户的问题。

【检索到的相关内容】
{context}

【用户问题】
{question}

【回答要求】
1. 引用相关标准编号（如 IEC、EN、GB、ASTM、UL 等）
2. 如涉及多国市场，请分别列出不同国家的标准要求
3. 如涉及有害物质，请注明具体限值
4. 如检索内容不足以回答，请明确告知用户并建议补充查询方向
5. 回答应符合 ISO/IEC 17025 实验室管理规范"""


def _prepare_qa_context(question: str, category: str = "all") -> tuple[str, list[str]]:
    """准备问答上下文和来源"""
    docs = search_knowledge(question, category=category, k=8)
    if docs:
        context = "\n".join([doc.page_content for doc in docs])
        sources = list(set([doc.metadata.get("source", "") for doc in docs if doc.metadata.get("source")]))
    else:
        context = "（知识库暂无相关数据，请基于通用检测知识回答）"
        sources = []
    return context, sources


def run_qa(question: str, category: str = "all") -> dict:
    """执行智能问答（同步版）"""
    llm = get_text_llm()
    context, sources = _prepare_qa_context(question, category)
    prompt = ChatPromptTemplate.from_template(QA_PROMPT)
    chain = prompt | llm
    result = chain.invoke({"context": context, "question": question})
    return {"answer": result.content, "sources": sources}


async def stream_qa(question: str, category: str = "all") -> AsyncGenerator[str, None]:
    """流式问答：使用 DashScope SDK 原生流式 API，实现真正的逐 token 输出"""
    settings = get_settings()
    context, sources = _prepare_qa_context(question, category)

    # 第一条 SSE：发送来源
    yield f"data: {json.dumps({'type': 'sources', 'sources': sources}, ensure_ascii=False)}\n\n"

    # 构建消息
    messages = [
        {"role": "system", "content": QA_PROMPT.replace("{context}", context).replace("{question}", question)},
    ]

    # 在线程中运行阻塞的流式迭代，通过队列传递给异步生成器
    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def _stream_worker():
        try:
            responses = Generation.call(
                model=settings.qwen_text_model,
                messages=messages,
                result_format="message",
                stream=True,
                incremental_output=True,
                api_key=settings.dashscope_api_key,
            )
            for response in responses:
                if response.status_code == 200:
                    content = response.output.choices[0].message.get("content", "")
                    if content:
                        loop.call_soon_threadsafe(queue.put_nowait, content)
        except Exception:
            pass
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    loop.run_in_executor(None, _stream_worker)

    while True:
        content = await queue.get()
        if content is None:
            break
        yield f"data: {json.dumps({'type': 'token', 'content': content}, ensure_ascii=False)}\n\n"

    # 结束标记
    yield "data: [DONE]\n\n"
