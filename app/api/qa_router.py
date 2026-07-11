"""智能问答 API 路由"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.models.schemas import QARequest, QAResponse
from app.agents.qa_agent import run_qa, stream_qa

router = APIRouter()


@router.post("/ask", response_model=QAResponse)
async def ask_question(request: QARequest):
    """AI 智能问答（完整响应）"""
    try:
        result = run_qa(
            question=request.question,
            category=request.category or "all",
        )
        return QAResponse(
            answer=result["answer"],
            sources=result.get("sources", []),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"问答服务出错: {str(e)}")


@router.post("/ask/stream")
async def ask_question_stream(request: QARequest):
    """AI 智能问答（SSE 流式输出）"""
    try:
        return StreamingResponse(
            stream_qa(
                question=request.question,
                category=request.category or "all",
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"问答流式服务出错: {str(e)}")
