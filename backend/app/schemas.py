from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------- 健康检查 ---------------------------- #

class HealthResponse(BaseModel):
    status: str
    app: str
    version: str


# ---------------------------- 任务（替代原 /analyze） ---------------------------- #

class TaskCreateRequest(BaseModel):
    resume_text: str = Field(..., min_length=1, description="简历原文")
    jd_text: str = Field("", description="目标岗位 JD（可选）")
    user_notes: str = Field("", description="求职者补充建议/期望（可选）")
    target_position: str = Field("", description="目标岗位名称（可选）")


class TaskCreateResponse(BaseModel):
    task_id: str
    record_id: int


class TaskStatus(BaseModel):
    """轮询响应：任务整体状态 + 最新一轮迭代结果 + 迭代进度。"""
    record_id: int
    status: str
    current_step: Optional[str] = None
    current_round: int = 0
    max_rounds: int = 3
    target_position: Optional[str] = None
    # 最新一轮迭代产物（供前端展示本轮稿件+评分+修改意见）
    latest_iteration: Optional[dict] = None
    # 首轮一次性产物（解析+JD分析，可空）
    parsed_resume: Optional[dict] = None
    jd_analysis: Optional[dict] = None
    error: Optional[str] = None


class TaskActionResponse(BaseModel):
    task_id: Optional[str] = None
    status: str
    message: Optional[str] = None


# ---------------------------- 历史记录 ---------------------------- #

class RecordListItem(BaseModel):
    id: int
    created_at: Optional[str] = None
    target_position: Optional[str] = None
    overall_score: Optional[float] = None
    current_round: int = 0
    status: str


class IterationItem(BaseModel):
    round_number: int
    optimization_advice: Optional[dict] = None
    rewritten_resume: Optional[str] = None
    final_qc: Optional[dict] = None
    qc_passed: Optional[bool] = None
    fix_instructions: Optional[list] = None
    created_at: Optional[str] = None


class RecordDetail(BaseModel):
    id: int
    created_at: Optional[str] = None
    resume_text: str
    jd_text: str
    user_notes: str
    target_position: Optional[str] = None
    parsed_resume: Optional[dict] = None
    jd_analysis: Optional[dict] = None
    current_round: int = 0
    status: str
    error: Optional[str] = None
    iterations: list[IterationItem] = []
