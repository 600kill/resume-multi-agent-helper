"""任务与历史接口：异步 /api/analyze + /api/records/{id} 轮询。

- POST /api/analyze：建 record + 入队 RQ，立即返回 record_id
- GET /api/records/{id}：返回状态 + 当前步骤 + 最新迭代（供前端轮询）
- GET /api/records：当前用户历史列表
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..config import get_settings
from ..db import get_db
from ..models import AnalysisRecord, Iteration, User
from ..schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    IterationItem,
    RecordDetail,
    RecordListItem,
    TaskStatus,
)
from ..worker import enqueue_analysis, get_step_from_redis

router = APIRouter(prefix="/api", tags=["tasks"])

settings = get_settings()


# ---------------------------- 健康 ---------------------------- #

@router.get("/health", response_model=dict)
def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "version": settings.version}


# ---------------------------- 异步分析 ---------------------------- #

@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(
    req: AnalyzeRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> AnalyzeResponse:
    """异步分析：建 record + 入队 RQ，立即返回 record_id，后台执行 LangGraph。"""
    rec = AnalysisRecord(
        user_id=current.id,
        resume_text=req.resume_text,
        jd_text=req.jd_text,
        user_notes=req.user_notes,
        target_position=req.target_position,
        mode=req.mode,
        status="pending",
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    task_id = enqueue_analysis(rec.id)
    return AnalyzeResponse(record_id=rec.id, task_id=task_id)


# 兼容旧接口 /api/tasks（行为同 /api/analyze）
@router.post("/tasks", response_model=AnalyzeResponse)
def create_task(
    req: AnalyzeRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> AnalyzeResponse:
    return analyze(req, db, current)


# ---------------------------- 轮询状态 ---------------------------- #

@router.get("/tasks/{record_id}", response_model=TaskStatus)
def get_task_status(
    record_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> TaskStatus:
    """轮询任务状态（兼容旧前端）。"""
    rec = db.get(AnalysisRecord, record_id)
    if rec is None or rec.user_id != current.id:
        raise HTTPException(status_code=404, detail="任务不存在")

    step_info = get_step_from_redis(record_id) or {}
    step = step_info.get("step") or rec.current_step
    desc = step_info.get("desc") or rec.current_step_desc
    round_num = step_info.get("iteration_round") or rec.iteration_round or 0

    latest_iter = (
        db.query(Iteration)
        .filter(Iteration.record_id == record_id)
        .order_by(Iteration.round_number.desc())
        .first()
    )

    return TaskStatus(
        record_id=record_id,
        status=rec.status,
        current_step=step,
        current_step_name=rec.current_step_name,
        current_step_desc=desc,
        iteration_round=round_num,
        max_rounds=settings.max_qc_rounds,
        target_position=rec.target_position,
        latest_iteration=_iteration_to_dict(latest_iter) if latest_iter else None,
        parsed_resume=rec.parsed_resume,
        jd_analysis=rec.jd_analysis,
        mode=rec.mode or "optimize",
        baseline_qc=rec.baseline_qc,
        error=rec.error,
        failed_step=rec.failed_step,
        cache_hit=bool(rec.cache_hit),
        created_at=rec.created_at.isoformat() if rec.created_at else None,
    )


# ---------------------------- 历史记录 ---------------------------- #

@router.get("/records", response_model=list[RecordListItem])
def list_records(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
    limit: int = 20,
) -> list[RecordListItem]:
    """当前用户的任务列表。"""
    rows = (
        db.query(AnalysisRecord)
        .filter(AnalysisRecord.user_id == current.id)
        .order_by(AnalysisRecord.created_at.desc())
        .limit(min(limit, 100))
        .all()
    )
    out = []
    for r in rows:
        latest = (
            db.query(Iteration)
            .filter(Iteration.record_id == r.id)
            .order_by(Iteration.round_number.desc())
            .first()
        )
        score = None
        if latest and isinstance(latest.final_qc, dict):
            score = latest.final_qc.get("overall_score")
        out.append(
            RecordListItem(
                id=r.id,
                created_at=r.created_at.isoformat() if r.created_at else None,
                target_position=r.target_position,
                overall_score=score,
                current_round=r.current_round,
                status=r.status,
                mode=r.mode or "optimize",
            )
        )
    return out


@router.get("/records/{record_id}", response_model=RecordDetail)
def get_record(
    record_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> RecordDetail:
    """任务详情：原始输入 + 所有迭代版本 + 当前步骤（供前端轮询）。"""
    rec = db.get(AnalysisRecord, record_id)
    if rec is None or rec.user_id != current.id:
        raise HTTPException(status_code=404, detail="记录不存在")

    # 从 Redis 取实时步骤（比 DB 更及时）
    step_info = get_step_from_redis(record_id) or {}
    step = step_info.get("step") or rec.current_step
    desc = step_info.get("desc") or rec.current_step_desc
    round_num = step_info.get("iteration_round") or rec.iteration_round or 0

    iterations = (
        db.query(Iteration)
        .filter(Iteration.record_id == record_id)
        .order_by(Iteration.round_number.asc())
        .all()
    )
    return RecordDetail(
        id=rec.id,
        created_at=rec.created_at.isoformat() if rec.created_at else None,
        resume_text=rec.resume_text,
        jd_text=rec.jd_text,
        user_notes=rec.user_notes,
        target_position=rec.target_position,
        parsed_resume=rec.parsed_resume,
        jd_analysis=rec.jd_analysis,
        mode=rec.mode or "optimize",
        baseline_qc=rec.baseline_qc,
        current_round=rec.current_round,
        iteration_round=round_num,
        status=rec.status,
        current_step=step,
        current_step_name=rec.current_step_name,
        current_step_desc=desc,
        error=rec.error,
        failed_step=rec.failed_step,
        cache_hit=bool(rec.cache_hit),
        iterations=[
            IterationItem(
                round_number=it.round_number,
                optimization_advice=it.optimization_advice,
                rewritten_resume=it.rewritten_resume,
                final_qc=it.final_qc,
                qc_passed=it.qc_passed,
                fix_instructions=it.fix_instructions,
                created_at=it.created_at.isoformat() if it.created_at else None,
            )
            for it in iterations
        ],
    )


# ---------------------------- 辅助 ---------------------------- #

def _iteration_to_dict(it: Iteration) -> dict:
    return {
        "round_number": it.round_number,
        "optimization_advice": it.optimization_advice,
        "rewritten_resume": it.rewritten_resume,
        "final_qc": it.final_qc,
        "qc_passed": it.qc_passed,
        "fix_instructions": it.fix_instructions,
        "created_at": it.created_at.isoformat() if it.created_at else None,
    }
