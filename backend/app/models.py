import json
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class AnalysisRecord(Base):
    """一次简历分析任务的完整记录。"""

    __tablename__ = "analysis_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # 输入
    resume_text: Mapped[str] = mapped_column(Text)
    jd_text: Mapped[str] = mapped_column(Text, default="")
    user_notes: Mapped[str] = mapped_column(Text, default="")

    # 输入的相关岗位
    target_position: Mapped[Optional[str]] = mapped_column(String(255), default="")

    # 各 Agent 输出
    parsed_resume: Mapped[Optional[dict]] = mapped_column(JSON)      # 简历解析者
    jd_analysis: Mapped[Optional[dict]] = mapped_column(JSON)        # JD 分析师
    optimization_advice: Mapped[Optional[dict]] = mapped_column(JSON)  # 求职简历顾问
    rewritten_resume: Mapped[Optional[str]] = mapped_column(Text)    # 简历改写员

    # HR 质检结果
    final_qc: Mapped[Optional[dict]] = mapped_column(JSON)
    qc_rounds: Mapped[int] = mapped_column(Integer, default=0)

    # 整体状态
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending|running|done|error
    error: Mapped[Optional[str]] = mapped_column(Text)