"""异步任务定义 - 报告审核 / 知识库更新"""

from workers.celery_app import celery_app


@celery_app.task(name="review_report_async")
def review_report_async(application_path: str, split_table_path: str, report_path: str):
    """异步执行报告审核"""
    from app.agents.review_agent import run_review
    from app.services.document_parser import (
        parse_application_form, parse_split_table,
        parse_report, parse_table_to_text,
    )

    app_data = parse_application_form(application_path)
    app_text = parse_table_to_text(app_data)

    split_data = parse_split_table(split_table_path)
    split_text = parse_table_to_text(split_data)

    report_text = parse_report(report_path)

    return run_review(app_text, split_text, report_text)


@celery_app.task(name="update_knowledge_base")
def update_knowledge_base(file_path: str, category: str = "all"):
    """异步更新知识库"""
    from app.services.knowledge_base import add_documents_to_kb
    from langchain_community.document_loaders import (
        TextLoader, PyPDFLoader, UnstructuredWordDocumentLoader,
    )
    import os

    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".txt":
        loader = TextLoader(file_path, encoding="utf-8")
    elif ext == ".pdf":
        loader = PyPDFLoader(file_path)
    elif ext == ".docx":
        loader = UnstructuredWordDocumentLoader(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {ext}")

    docs = loader.load()
    count = add_documents_to_kb(docs, category)
    return {"file": file_path, "category": category, "chunks_added": count}
