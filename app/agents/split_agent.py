"""样板拆分 LangGraph Agent"""

import os
import json
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_core.prompts import ChatPromptTemplate
from app.models.llm import get_text_llm
from app.services.image_analyzer import analyze_product_image, render_split_diagram
from app.config import UPLOADS_DIR


class SplitState(TypedDict):
    image_path: str
    analysis: dict
    diagram_path: str
    quality_ok: bool


def run_split(image_path: str) -> dict:
    """执行样板拆分分析"""
    # 1. 多模态模型分析产品图片
    try:
        analysis = analyze_product_image(image_path)
    except Exception as e:
        return {
            "analysis": {
                "product_name": "分析失败",
                "components": [],
                "overall_structure": f"图像分析出错: {str(e)}",
            },
            "diagram_path": None,
            "error": str(e),
        }

    # 2. 渲染拆分示意图
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    diagram_path = os.path.join(UPLOADS_DIR, f"{base_name}_split.png")
    try:
        render_split_diagram(analysis, diagram_path)
    except Exception as e:
        diagram_path = None

    # 3. AI 自审拆分结果
    llm = get_text_llm()
    review_prompt = ChatPromptTemplate.from_template(
        "请审核以下产品拆分结果是否合理，回答'合理'或提出修改建议：\n{analysis}"
    )
    chain = review_prompt | llm
    review_result = chain.invoke({"analysis": json.dumps(analysis, ensure_ascii=False)})
    quality_ok = "合理" in review_result.content

    return {
        "analysis": analysis,
        "diagram_path": diagram_path,
        "quality_ok": quality_ok,
    }
