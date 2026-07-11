"""报告审核 API 路由"""

import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from app.models.schemas import ReviewResponse, ReviewResult, FileUploadResponse
from app.agents.review_agent import run_review, stream_review
from app.services.document_parser import (
    parse_application_form,
    parse_split_table,
    parse_report,
    parse_table_to_text,
)
from app.config import UPLOADS_DIR

router = APIRouter()


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...), file_type: str = "report"):
    """上传审核文件（申请表/拆分表/报告）"""
    ext = os.path.splitext(file.filename)[1].lower()
    allowed = (".xlsx", ".xls", ".csv", ".pdf", ".docx", ".txt")
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {ext}")

    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOADS_DIR, filename)
    os.makedirs(UPLOADS_DIR, exist_ok=True)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    return FileUploadResponse(
        filename=file.filename,
        file_path=filename,
        file_type=file_type,
    )


@router.post("/review", response_model=ReviewResponse)
async def review_report(
    application_filename: str,
    split_table_filename: str,
    report_filename: str,
):
    """执行报告审核（五步审核工作流）"""
    app_text, split_text, report_text = _parse_review_files(
        application_filename, split_table_filename, report_filename
    )

    # 执行五步审核
    result = run_review(app_text, split_text, report_text)

    return ReviewResponse(
        result=ReviewResult(**result),
        message=f"审核完成，发现 {result['total_issues']} 个问题",
    )


def _parse_review_files(application_filename: str, split_table_filename: str, report_filename: str):
    """解析审核文件，返回文本内容"""
    app_path = os.path.join(UPLOADS_DIR, application_filename)
    split_path = os.path.join(UPLOADS_DIR, split_table_filename)
    report_path = os.path.join(UPLOADS_DIR, report_filename)

    for path, name in [(app_path, "申请表"), (split_path, "拆分表"), (report_path, "报告")]:
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail=f"{name}文件不存在")

    try:
        app_data = parse_application_form(app_path)
        app_text = parse_table_to_text(app_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"申请表解析失败: {str(e)}")

    try:
        split_data = parse_split_table(split_path)
        split_text = parse_table_to_text(split_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"拆分表解析失败: {str(e)}")

    try:
        report_text = parse_report(report_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"报告解析失败: {str(e)}")

    return app_text, split_text, report_text


@router.post("/review/stream")
async def review_report_stream(
    application_filename: str,
    split_table_filename: str,
    report_filename: str,
):
    """流式报告审核（SSE）：逐步进度 + 流式最终报告"""
    app_text, split_text, report_text = _parse_review_files(
        application_filename, split_table_filename, report_filename
    )
    return StreamingResponse(
        stream_review(app_text, split_text, report_text),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
