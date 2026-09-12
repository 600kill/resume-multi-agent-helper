"""分析服务：负责运行 LangGraph 流水线并持久化到 DB。

拆分为两个入口：
- run_first_round：5 个 Agent 全跑（parser‖jd_analyst→advisor→rewriter→hr_qc）
- run_next_round：3 个 Agent（advisor→rewriter→hr_qc），基于上轮 fix_instructions

每完成一个节点即更新 DB.current_step 与 Redis step key，供前端轮询。
Graph 不再自动回环，每轮 QC 后停止，由 /iterate 接口触发下一轮。
"""

import logging
from typing import Callable, Optional

from redis import Redis

from ..config import get_settings
from ..db import SessionLocal
from ..models import AnalysisRecord, Iteration

logger = logging.getLogger("resume.service")

settings = get_settings()

_graph: Optional[Callable] = None
_iter_graph: Optional[Callable] = None


def get_graph() -> Callable:
    global _graph
    if _graph is None:
        from .graph import build_graph
        _graph = build_graph()
    return _graph


def get_iteration_graph() -> Callable:
    global _iter_graph
    if _iter_graph is None:
        from .graph import build_iteration_graph
        _iter_graph = build_iteration_graph()
    return _iter_graph


# ---------------------------- 进度上报 ---------------------------- #

def _set_step(record_id: int, step: Optional[str], status: Optional[str] = None) -> None:
    """更新 DB.current_step + Redis task:{id}:step（供前端轮询）。"""
    try:
        conn = Redis.from_url(settings.redis_url, decode_responses=True)
        if step:
            conn.set(f"resume:task:{record_id}:step", step, ex=7200)
        else:
            conn.delete(f"resume:task:{record_id}:step")
    except Exception as e:
        logger.warning("redis set step failed: %s", e)

    db = SessionLocal()
    try:
        rec = db.get(AnalysisRecord, record_id)
        if rec is not None:
            rec.current_step = step
            if status:
                rec.status = status
            db.commit()
    except Exception as e:
        logger.warning("db set step failed: %s", e)
    finally:
        db.close()


def _stream_with_progress(graph: Callable, initial: dict, record_id: int) -> dict:
    """以 stream 模式运行 graph，每完成一个节点更新 current_step。

    返回最终聚合后的 state（与 graph.invoke 等价）。
    """
    state: dict = dict(initial)
    for chunk in graph.stream(initial, stream_mode="updates"):
        # chunk 形如 {"advisor": {"optimization_advice": {...}, ...}}
        for node_name, update in chunk.items():
            if isinstance(update, dict):
                state.update(update)
            _set_step(record_id, node_name)
    return state


# ---------------------------- 首轮 ---------------------------- #

def run_first_round(
    record_id: int,
    resume_text: str,
    jd_text: str = "",
    user_notes: str = "",
    target_position: str = "",
) -> dict:
    """执行首轮流水线：5 个 Agent，写 analysis_records.parsed_resume/jd_analysis + iterations(round=1)。"""
    _set_step(record_id, "starting", status="running")

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
        "fix_instructions": None,
        "iteration_round": 1,
        "messages": [],
    }

    result = _stream_with_progress(get_graph(), initial, record_id)

    # 持久化首轮一次性产物到 analysis_records
    db = SessionLocal()
    try:
        rec = db.get(AnalysisRecord, record_id)
        if rec is None:
            return {"error": "record not found"}
        rec.parsed_resume = result.get("parsed_resume")
        rec.jd_analysis = result.get("jd_analysis")

        # 写 iterations round=1
        it = Iteration(
            record_id=record_id,
            round_number=1,
            optimization_advice=result.get("optimization_advice"),
            rewritten_resume=result.get("rewritten_resume"),
            final_qc=result.get("final_qc"),
            qc_passed=result.get("qc_passed"),
            fix_instructions=result.get("fix_instructions"),
        )
        db.add(it)
        rec.current_round = 1
        rec.current_step = None
        rec.status = "iterating"
        db.commit()
    finally:
        db.close()

    _set_step(record_id, None)  # 清空 Redis step
    return {
        "parsed_resume": result.get("parsed_resume"),
        "jd_analysis": result.get("jd_analysis"),
        "optimization_advice": result.get("optimization_advice"),
        "rewritten_resume": result.get("rewritten_resume"),
        "final_qc": result.get("final_qc"),
        "qc_passed": result.get("qc_passed"),
        "fix_instructions": result.get("fix_instructions"),
        "round_number": 1,
    }


# ---------------------------- 迭代轮 ---------------------------- #

def run_next_round(record_id: int) -> dict:
    """执行迭代轮：advisor→rewriter→hr_qc（基于上轮 fix_instructions）。"""
    db = SessionLocal()
    try:
        rec = db.get(AnalysisRecord, record_id)
        if rec is None:
            return {"error": "record not found"}
        if rec.current_round >= settings.max_qc_rounds:
            return {"error": "已达最大迭代轮次"}
        if rec.status == "stopped":
            return {"error": "任务已停止"}

        # 取上一轮 iteration 的 fix_instructions + 首轮 parsed/jd
        last_iter = (
            db.query(Iteration)
            .filter(Iteration.record_id == record_id)
            .order_by(Iteration.round_number.desc())
            .first()
        )
        if last_iter is None:
            return {"error": "无首轮结果，无法迭代"}

        next_round = rec.current_round + 1
        initial: dict = {
            "resume_text": rec.resume_text,
            "jd_text": rec.jd_text,
            "user_notes": rec.user_notes,
            "target_position": rec.target_position,
            "parsed_resume": rec.parsed_resume,
            "jd_analysis": rec.jd_analysis,
            "optimization_advice": None,
            "rewritten_resume": None,
            "final_qc": None,
            "qc_passed": None,
            "qc_rounds": next_round,
            "fix_instructions": last_iter.fix_instructions,
            "iteration_round": next_round,
            "messages": [],
        }
        inputs_ready = True
    finally:
        db.close()

    if not inputs_ready:
        return {"error": "prepare failed"}

    _set_step(record_id, "starting", status="iterating")
    result = _stream_with_progress(get_iteration_graph(), initial, record_id)

    # 持久化本轮迭代
    db = SessionLocal()
    try:
        rec = db.get(AnalysisRecord, record_id)
        if rec is None:
            return {"error": "record not found"}
        it = Iteration(
            record_id=record_id,
            round_number=next_round,
            optimization_advice=result.get("optimization_advice"),
            rewritten_resume=result.get("rewritten_resume"),
            final_qc=result.get("final_qc"),
            qc_passed=result.get("qc_passed"),
            fix_instructions=result.get("fix_instructions"),
        )
        db.add(it)
        rec.current_round = next_round
        rec.current_step = None
        # 达到最大轮次或质检通过 → done；否则保持 iterating 等用户决定
        if next_round >= settings.max_qc_rounds or result.get("qc_passed"):
            rec.status = "done"
        else:
            rec.status = "iterating"
        db.commit()
    finally:
        db.close()

    _set_step(record_id, None)
    return {
        "optimization_advice": result.get("optimization_advice"),
        "rewritten_resume": result.get("rewritten_resume"),
        "final_qc": result.get("final_qc"),
        "qc_passed": result.get("qc_passed"),
        "fix_instructions": result.get("fix_instructions"),
        "round_number": next_round,
    }
