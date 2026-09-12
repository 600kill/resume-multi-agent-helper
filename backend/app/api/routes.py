from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..agents.service import run_analysis
from ..cache import cache_get_json, cache_set_json, make_cache_key
from ..config import get_settings
from ..db import get_db
from ..models import AnalysisRecord
from ..schemas import AnalysisRequest, AnalysisResponse

router = APIRouter(prefix="/api", tags=["analysis"])

settings = get_settings()


@router.get("/health", response_model=dict)
def health() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.version,
    }


@router.get("/records", response_model=list)
def list_records(db: Session = Depends(get_db), limit: int = 20) -> list:
    rows = (
        db.query(AnalysisRecord)
        .order_by(AnalysisRecord.created_at.desc())
        .limit(min(limit, 100))
        .all()
    )
    return [
        {
            "id": r.id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "target_position": r.target_position,
            "status": r.status,
            "overall_score": (r.final_qc or {}).get("overall_score")
            if isinstance(r.final_qc, dict)
            else None,
        }
        for r in rows
    ]


@router.get("/records/{record_id}", response_model=dict)
def get_record(record_id: int, db: Session = Depends(get_db)) -> dict:
    rec = db.get(AnalysisRecord, record_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {
        "id": rec.id,
        "created_at": rec.created_at.isoformat() if rec.created_at else None,
        "resume_text": rec.resume_text,
        "jd_text": rec.jd_text,
        "user_notes": rec.user_notes,
        "target_position": rec.target_position,
        "parsed_resume": rec.parsed_resume,
        "jd_analysis": rec.jd_analysis,
        "optimization_advice": rec.optimization_advice,
        "rewritten_resume": rec.rewritten_resume,
        "final_qc": rec.final_qc,
        "qc_rounds": rec.qc_rounds,
        "status": rec.status,
        "error": rec.error,
    }


@router.post("/analyze", response_model=AnalysisResponse)
def analyze(req: AnalysisRequest, db: Session = Depends(get_db)) -> AnalysisResponse:
    # 建初始记录
    rec = AnalysisRecord(
        resume_text=req.resume_text,
        jd_text=req.jd_text,
        user_notes=req.user_notes,
        target_position=req.target_position,
        status="running",
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    # 主流程缓存：key 只由输入内容决定（排序哈希），同内容重复请求可命中
    content_key = make_cache_key(
        "analysis",
        resume_text=req.resume_text,
        jd_text=req.jd_text,
        user_notes=req.user_notes,
        target_position=req.target_position,
    )
    meta = {"record_id": rec.id, "target_position": req.target_position}
    cached = cache_get_json(content_key, metadata=meta)
    if cached:
        rec.status = "done"
        for field in ("parsed_resume", "jd_analysis", "optimization_advice", "rewritten_resume", "final_qc"):
            setattr(rec, field, cached.get(field))
        rec.qc_rounds = cached.get("qc_rounds", 0)
        db.commit()
        return AnalysisResponse(record_id=rec.id, **cached)

    try:
        summary = run_analysis(
            resume_text=req.resume_text,
            jd_text=req.jd_text,
            user_notes=req.user_notes,
            target_position=req.target_position,
            record_id=rec.id,
        )
    except Exception as e:
        rec.status = "error"
        rec.error = str(e)
        db.commit()
        return AnalysisResponse(error=str(e))

    cache_set_json(content_key, summary, ttl=settings.cache_ttl)
    return AnalysisResponse(record_id=rec.id, **summary)