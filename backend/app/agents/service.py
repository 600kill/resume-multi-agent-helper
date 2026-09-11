"""分析服务：负责运行 LangGraph 流水线，持久化结果，并做 Redis 缓存。"""

from typing import Callable, Optional

from ..cache import cache_get_json, cache_key, cache_set_json
from ..config import get_settings
from ..db import SessionLocal
from ..models import AnalysisRecord
from .graph import build_graph

settings = get_settings()

_graph: Optional[Callable] = None


def get_graph() -> Callable:
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def run_analysis(
    resume_text: str,
    jd_text: str = "",
    user_notes: str = "",
    target_position: str = "",
    record_id: int | None = None,
) -> dict:
    """执行完整分析流水线，返回结构化结果，并写入 DB 与 Redis 缓存。"""

    graph = get_graph()
    initial: dict = {
        "resume_text": resume_text,
        "jd_text": jd_text,
        "user_notes": user_notes,
        "target_position": target_position,
        "parsed_resume": None,
        "jd_analysis": None,
        "optimization_advice": None,
        "rewritten_resume": None,
        "final_qc": None,
        "qc_passed": None,
        "qc_rounds": 0,
        "messages": [],
    }

    result = graph.invoke(initial)
    summary = {
        "parsed_resume": result.get("parsed_resume"),
        "jd_analysis": result.get("jd_analysis"),
        "optimization_advice": result.get("optimization_advice"),
        "rewritten_resume": result.get("rewritten_resume"),
        "final_qc": result.get("final_qc"),
        "qc_rounds": result.get("qc_rounds", 0),
    }

    # 持久化到 DB
    try:
        _persist(record_id, resume_text, jd_text, user_notes, target_position, summary)
    except Exception as e:  # 持久化失败不影响返回结果
        summary["_db_warning"] = str(e)

    # 写缓存
    cache_set_json(cache_key("analysis", "raw", target_position, resume_text[:60]), summary)
    return summary


def _persist(
    record_id: int | None,
    resume_text: str,
    jd_text: str,
    user_notes: str,
    target_position: str,
    summary: dict,
) -> None:
    session = SessionLocal()
    try:
        if record_id is not None:
            rec = session.get(AnalysisRecord, record_id)
            if rec is not None:
                rec.status = "done"
                rec.parsed_resume = summary.get("parsed_resume")
                rec.jd_analysis = summary.get("jd_analysis")
                rec.optimization_advice = summary.get("optimization_advice")
                rec.rewritten_resume = summary.get("rewritten_resume")
                rec.final_qc = summary.get("final_qc")
                rec.qc_rounds = summary.get("qc_rounds", 0)
                session.commit()
                return
        rec = AnalysisRecord(
            resume_text=resume_text,
            jd_text=jd_text,
            user_notes=user_notes,
            target_position=target_position,
            parsed_resume=summary.get("parsed_resume"),
            jd_analysis=summary.get("jd_analysis"),
            optimization_advice=summary.get("optimization_advice"),
            rewritten_resume=summary.get("rewritten_resume"),
            final_qc=summary.get("final_qc"),
            qc_rounds=summary.get("qc_rounds", 0),
            status="done",
        )
        session.add(rec)
        session.commit()
    finally:
        session.close()