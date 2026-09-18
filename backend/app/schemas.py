from typing import Literal, Optional

from pydantic import BaseModel, Field


# 工作模式：optimize=直接优化后测评（选项一）；compare=原始测评→优化→再测评（选项二）
AnalyzeMode = Literal["optimize", "compare"]


# ---------------------------- 健康检查 ---------------------------- #

class HealthResponse(BaseModel):
    status: str
    app: str
    version: str


# ---------------------------- 分析任务 ---------------------------- #

class AnalyzeRequest(BaseModel):
    resume_text: str = Field(..., min_length=1, description="简历原文")
    jd_text: str = Field("", description="目标岗位 JD（可选）")
    user_notes: str = Field("", description="求职者补充建议/期望（可选）")
    target_position: str = Field("", description="目标岗位名称（可选）")
    mode: AnalyzeMode = Field("optimize", description="工作模式：optimize=直接优化后测评；compare=前后对比测评")


class AnalyzeResponse(BaseModel):
    """异步提交响应：立即返回 record_id，后台执行 LangGraph。"""
    record_id: int
    task_id: str


class TaskStatus(BaseModel):
    """轮询响应：任务整体状态 + 当前步骤 + 最新一轮迭代结果。"""
    record_id: int
    status: str
    current_step: Optional[str] = None
    current_step_name: Optional[str] = None
    current_step_desc: Optional[str] = None
    iteration_round: int = 0
    max_rounds: int = 3
    target_position: Optional[str] = None
    latest_iteration: Optional[dict] = None
    parsed_resume: Optional[dict] = None
    jd_analysis: Optional[dict] = None
    mode: str = "optimize"
    baseline_qc: Optional[dict] = None
    error: Optional[str] = None
    failed_step: Optional[str] = None
    cache_hit: bool = False
    created_at: Optional[str] = None


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
    mode: str = "optimize"


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
    mode: str = "optimize"
    baseline_qc: Optional[dict] = None
    current_round: int = 0
    iteration_round: int = 0
    status: str
    current_step: Optional[str] = None
    current_step_name: Optional[str] = None
    current_step_desc: Optional[str] = None
    error: Optional[str] = None
    failed_step: Optional[str] = None
    cache_hit: bool = False
    iterations: list[IterationItem] = []
