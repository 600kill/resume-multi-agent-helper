"""任务与历史接口：替代旧 /api/analyze，使用 RQ 异步队列。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..cache import cache_get_json, cache_set_json, make_cache_key
from ..config import get_settings
from ..db import get_db
from ..models import AnalysisRecord, Iteration, User
from ..schemas import (
    IterationItem,
    RecordDetail,
    RecordListItem,
    TaskActionResponse,
    TaskCreateRequest,
    TaskCreateResponse,
    TaskStatus,
)
from ..worker import enqueue_first_round, enqueue_next_round, get_step_from_redis

router = APIRouter(prefix="/api", tags=["tasks"])

settings = get_settings()


# ---------------------------- 健康 ---------------------------- #

@router.get("/health", response_model=dict)
def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "version": settings.version}


# ---------------------------- 任务（异步队列） ---------------------------- #

@router.post("/tasks", response_model=TaskCreateResponse)
def create_task(
    req: TaskCreateRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> TaskCreateResponse:
    """建 record + 入队首轮任务，返回 task_id + record_id。"""
    rec = AnalysisRecord(
        user_id=current.id,
        resume_text=req.resume_text,
        jd_text=req.jd_text,
        user_notes=req.user_notes,
        target_position=req.target_position,
        status="pending",
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    task_id = enqueue_first_round(rec.id)
    return TaskCreateResponse(task_id=task_id, record_id=rec.id)


@router.get("/tasks/{record_id}", response_model=TaskStatus)
def get_task_status(
    record_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> TaskStatus:
    """轮询任务状态：返回 status/current_step/最新 iteration/迭代进度。"""
    rec = db.get(AnalysisRecord, record_id)
    if rec is None or rec.user_id != current.id:
        raise HTTPException(status_code=404, detail="任务不存在")

    # current_step：优先读 Redis（实时性更高），DB 作为兜底
    step = get_step_from_redis(record_id) or rec.current_step

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
        current_round=rec.current_round,
        max_rounds=settings.max_qc_rounds,
        target_position=rec.target_position,
        latest_iteration=_iteration_to_dict(latest_iter) if latest_iter else None,
        parsed_resume=rec.parsed_resume,
        jd_analysis=rec.jd_analysis,
        error=rec.error,
    )


@router.post("/tasks/{record_id}/iterate", response_model=TaskActionResponse)
def iterate_task(
    record_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> TaskActionResponse:
    """触发下一轮迭代：校验轮次+状态，入队迭代任务。"""
    rec = db.get(AnalysisRecord, record_id)
    if rec is None or rec.user_id != current.id:
        raise HTTPException(status_code=404, detail="任务不存在")
    if rec.status == "stopped":
        raise HTTPException(status_code=400, detail="任务已停止，无法继续迭代")
    if rec.status == "error":
        raise HTTPException(status_code=400, detail="任务异常，无法继续迭代")
    if rec.current_round >= settings.max_qc_rounds:
        raise HTTPException(status_code=400, detail="已达最大迭代轮次（3轮）")
    if rec.current_round == 0:
        raise HTTPException(status_code=400, detail="首轮尚未完成，无法迭代")
    if rec.status == "running":
        raise HTTPException(status_code=400, detail="任务正在执行中，请等待完成")

    task_id = enqueue_next_round(record_id)
    return TaskActionResponse(task_id=task_id, status="iterating", message="已入队下一轮迭代")


@router.post("/tasks/{record_id}/stop", response_model=TaskActionResponse)
def stop_task(
    record_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> TaskActionResponse:
    """停止迭代：锁定当前稿件。"""
    rec = db.get(AnalysisRecord, record_id)
    if rec is None or rec.user_id != current.id:
        raise HTTPException(status_code=404, detail="任务不存在")
    if rec.status == "stopped":
        return TaskActionResponse(status="stopped", message="任务已停止")
    if rec.status == "done":
        return TaskActionResponse(status="done", message="任务已完成，无需停止")
    rec.status = "stopped"
    db.commit()
    return TaskActionResponse(status="stopped", message="任务已锁定，停止迭代")


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
            )
        )
    return out


@router.get("/records/{record_id}", response_model=RecordDetail)
def get_record(
    record_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> RecordDetail:
    """任务详情：原始输入 + 所有迭代版本。"""
    rec = db.get(AnalysisRecord, record_id)
    if rec is None or rec.user_id != current.id:
        raise HTTPException(status_code=404, detail="记录不存在")
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
        current_round=rec.current_round,
        status=rec.status,
        error=rec.error,
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
