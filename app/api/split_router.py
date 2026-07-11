"""样板拆分 API 路由"""

import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from app.models.schemas import SplitResponse, FileUploadResponse
from app.agents.split_agent import run_split
from app.config import UPLOADS_DIR

router = APIRouter()


@router.post("/upload", response_model=FileUploadResponse)
async def upload_product_image(file: UploadFile = File(...)):
    """上传产品图片"""
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".bmp"):
        raise HTTPException(status_code=400, detail="仅支持 JPG/PNG/BMP 图片格式")

    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOADS_DIR, filename)
    os.makedirs(UPLOADS_DIR, exist_ok=True)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    return FileUploadResponse(
        filename=file.filename,
        file_path=filename,
        file_type="image",
    )


@router.post("/analyze/{filename}", response_model=SplitResponse)
async def analyze_image(filename: str):
    """分析产品图片并生成拆分图"""
    file_path = os.path.join(UPLOADS_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="图片文件不存在")

    result = run_split(file_path)

    diagram_url = None
    if result.get("diagram_path") and os.path.exists(result["diagram_path"]):
        diagram_filename = os.path.basename(result["diagram_path"])
        diagram_url = f"/api/split/diagram/{diagram_filename}"

    return SplitResponse(
        analysis=result["analysis"],
        diagram_url=diagram_url,
        message="拆分分析完成" if result.get("quality_ok") else "拆分分析完成（AI建议复核）",
    )


@router.get("/diagram/{filename}")
async def get_diagram(filename: str):
    """获取拆分示意图"""
    file_path = os.path.join(UPLOADS_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="图片不存在")
    return FileResponse(file_path, media_type="image/png")
