"""AI检测助手 - FastAPI 主入口"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os

from app.api.qa_router import router as qa_router
from app.api.split_router import router as split_router
from app.api.review_router import router as review_router
from app.models.schemas import HealthResponse
from app.config import UPLOADS_DIR

app = FastAPI(
    title="AI检测助手",
    description="AI智能检测辅助系统",
    version="1.0.0",
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(qa_router, prefix="/api/qa", tags=["智能问答"])
app.include_router(split_router, prefix="/api/split", tags=["样板拆分"])
app.include_router(review_router, prefix="/api/review", tags=["报告审核"])

# 静态文件
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=FileResponse)
async def root():
    """返回前端首页"""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return FileResponse(os.path.join(os.path.dirname(os.path.dirname(__file__)), "index.html"))


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    return HealthResponse()


if __name__ == "__main__":
    import uvicorn
    from app.config import get_settings
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
    )
