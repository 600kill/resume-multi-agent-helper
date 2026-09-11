from typing import Optional

from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    resume_text: str = Field(..., min_length=1, description="简历原文")
    jd_text: str = Field("", description="目标岗位 JD（可选）")
    user_notes: str = Field("", description="求职者补充建议/期望（可选）")
    target_position: str = Field("", description="目标岗位名称（可选）")


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str


class AnalysisResponse(BaseModel):
    record_id: Optional[int] = None
    parsed_resume: dict = {}
    jd_analysis: dict = {}
    optimization_advice: dict = {}
    rewritten_resume: str = ""
    final_qc: dict = {}
    qc_rounds: int = 0
    error: Optional[str] = None