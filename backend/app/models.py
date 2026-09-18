from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class User(Base):
    """用户表：存储登录信息与哈希密码。"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    records: Mapped[list["AnalysisRecord"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class AnalysisRecord(Base):
    """一次简历分析任务：任务级（输入+状态+用户），每轮迭代产物存 iterations 子表。"""

    __tablename__ = "analysis_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # 归属用户
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # 输入
    resume_text: Mapped[str] = mapped_column(Text)
    jd_text: Mapped[str] = mapped_column(Text, default="")
    user_notes: Mapped[str] = mapped_column(Text, default="")
    target_position: Mapped[Optional[str]] = mapped_column(String(255), default="")

    # 首轮一次性产物（解析+JD分析，后续迭代复用）
    parsed_resume: Mapped[Optional[dict]] = mapped_column(JSON)
    jd_analysis: Mapped[Optional[dict]] = mapped_column(JSON)

    # 工作模式：optimize=直接优化后测评；compare=原始测评→优化→优化后测评（前后对比）
    mode: Mapped[str] = mapped_column(String(16), default="optimize")
    # compare 模式下原始简历的基线测评结果（optimize 模式为 None）
    baseline_qc: Mapped[Optional[dict]] = mapped_column(JSON)

    # 任务整体状态：pending|running|iterating|done|stopped|error
    status: Mapped[str] = mapped_column(String(32), default="pending")
    current_step: Mapped[Optional[str]] = mapped_column(String(32), default=None)  # parser|jd_analyst|advisor|rewriter|hr_qc
    current_step_name: Mapped[Optional[str]] = mapped_column(String(64), default=None)  # 节点名
    current_step_desc: Mapped[Optional[str]] = mapped_column(Text, default=None)        # 动态文案
    iteration_round: Mapped[int] = mapped_column(Integer, default=0)                     # 当前质检迭代轮次
    current_round: Mapped[int] = mapped_column(Integer, default=0)  # 已完成的迭代轮次
    error: Mapped[Optional[str]] = mapped_column(Text)
    failed_step: Mapped[Optional[str]] = mapped_column(String(64), default=None)  # 失败步骤名
    cache_hit: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)      # 缓存命中标记

    user: Mapped["User"] = relationship(back_populates="records")
    iterations: Mapped[list["Iteration"]] = relationship(
        back_populates="record", cascade="all, delete-orphan", order_by="Iteration.round_number"
    )


class Iteration(Base):
    """每轮迭代的产物：advisor 优化建议 + rewriter 改写稿件 + hr_qc 质检结果。"""

    __tablename__ = "iterations"
    __table_args__ = (UniqueConstraint("record_id", "round_number", name="uq_record_round"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record_id: Mapped[int] = mapped_column(ForeignKey("analysis_records.id", ondelete="CASCADE"), nullable=False, index=True)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 1, 2, 3
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # 本轮三 Agent 产物
    optimization_advice: Mapped[Optional[dict]] = mapped_column(JSON)
    rewritten_resume: Mapped[Optional[str]] = mapped_column(Text)
    final_qc: Mapped[Optional[dict]] = mapped_column(JSON)
    qc_passed: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    fix_instructions: Mapped[Optional[list]] = mapped_column(JSON)  # 下一轮要应用的修改指令

    record: Mapped["AnalysisRecord"] = relationship(back_populates="iterations")
