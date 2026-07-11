"""API 数据模型定义"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


# ==================== 智能问答 ====================
class QARequest(BaseModel):
    question: str = Field(..., description="用户提问内容")
    category: Optional[str] = Field(None, description="检测类别分区(可选)")


class QAResponse(BaseModel):
    answer: str = Field(..., description="AI回答内容")
    sources: list[str] = Field(default=[], description="引用的标准来源")


# ==================== 样板拆分 ====================
class SplitComponent(BaseModel):
    name: str
    material: str
    material_category: str
    quantity: int
    position: str
    test_items: list[str]
    applicable_standards: list[str] = []


class SplitResult(BaseModel):
    product_name: str
    components: list[SplitComponent]
    overall_structure: str
    diagram_path: Optional[str] = None


class SplitResponse(BaseModel):
    analysis: SplitResult
    diagram_url: Optional[str] = None
    message: str = "拆分分析完成"


# ==================== 报告审核 ====================
class ReviewRequest(BaseModel):
    application_file: Optional[str] = None
    split_table_file: Optional[str] = None
    report_file: Optional[str] = None


class IssueItem(BaseModel):
    field: str = ""
    description: str = ""
    severity: str = "轻微"
    expected: str = ""
    actual: str = ""


class ReviewResult(BaseModel):
    conclusion: str = Field(..., description="审核结论: 通过/需修改/不通过")
    consistency_issues: list[IssueItem] = []
    compliance_issues: list[IssueItem] = []
    completeness_issues: list[IssueItem] = []
    cnas_cma_issues: list[IssueItem] = []
    standard_version_issues: list[IssueItem] = []
    final_report: str = ""
    total_issues: int = 0


class ReviewResponse(BaseModel):
    result: ReviewResult
    message: str = "审核完成"


# ==================== 通用 ====================
class FileUploadResponse(BaseModel):
    filename: str
    file_path: str
    file_type: str
    message: str = "上传成功"


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
    service: str = "AI检测助手"
