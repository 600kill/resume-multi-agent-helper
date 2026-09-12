"""RQ 任务队列：入队接口 + Worker 执行的 job 函数。

Worker 进程（start_worker.ps1）会消费 "resume" 队列，
调用 service 层执行首轮/迭代轮流水线，并把进度写入 Redis 与 DB。
"""

import logging
from typing import Optional

from redis import Redis
from rq import Queue

from .agents.service import run_first_round, run_next_round
from .config import get_settings
from .db import SessionLocal
from .models import AnalysisRecord

logger = logging.getLogger("resume.worker")

settings = get_settings()


def get_queue() -> Queue:
    """获取 RQ 队列单例（连接 Redis）。

    RQ 内部期望 bytes，不能 decode_responses=True（否则 clean_registries 会失败）。
    """
    conn = Redis.from_url(settings.redis_url, decode_responses=False)
    return Queue("resume", connection=conn)


def set_step(record_id: int, step: str, status: Optional[str] = None) -> None:
    """把当前执行步骤写入 Redis（供前端轮询）+ DB.current_step。"""
    conn = None
    try:
        conn = Redis.from_url(settings.redis_url, decode_responses=True)
        conn.set(f"resume:task:{record_id}:step", step, ex=7200)
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


def run_first_round_job(record_id: int) -> dict:
    """Worker 执行：首轮流水线（5 Agent）。"""
    db = SessionLocal()
    try:
        rec = db.get(AnalysisRecord, record_id)
        if rec is None:
            return {"error": "record not found"}
        rec.status = "running"
        db.commit()
        inputs = {
            "resume_text": rec.resume_text,
            "jd_text": rec.jd_text,
            "user_notes": rec.user_notes,
            "target_position": rec.target_position,
        }
        return run_first_round(record_id=record_id, **inputs)
    except Exception as e:
        logger.exception("first round job failed")
        db = SessionLocal()
        try:
            rec = db.get(AnalysisRecord, record_id)
            if rec is not None:
                rec.status = "error"
                rec.error = str(e)
                rec.current_step = None
                db.commit()
        finally:
            db.close()
        return {"error": str(e)}
    finally:
        db.close()


def run_next_round_job(record_id: int) -> dict:
    """Worker 执行：迭代轮流水线（advisor→rewriter→hr_qc 3 Agent）。"""
    db = SessionLocal()
    try:
        rec = db.get(AnalysisRecord, record_id)
        if rec is None:
            return {"error": "record not found"}
        if rec.status not in ("iterating", "done", "stopped"):
            return {"error": f"invalid status for iteration: {rec.status}"}
        if rec.current_round >= settings.max_qc_rounds:
            return {"error": "已达最大迭代轮次"}
        if rec.status == "stopped":
            return {"error": "任务已停止"}
        rec.status = "iterating"
        db.commit()
        return run_next_round(record_id=record_id)
    except Exception as e:
        logger.exception("next round job failed")
        db = SessionLocal()
        try:
            rec = db.get(AnalysisRecord, record_id)
            if rec is not None:
                rec.status = "error"
                rec.error = str(e)
                rec.current_step = None
                db.commit()
        finally:
            db.close()
        return {"error": str(e)}
    finally:
        db.close()


def enqueue_first_round(record_id: int) -> str:
    """入队首轮任务，返回 RQ job id。"""
    job = get_queue().enqueue(run_first_round_job, record_id)
    return job.id


def enqueue_next_round(record_id: int) -> str:
    """入队迭代轮任务，返回 RQ job id。"""
    job = get_queue().enqueue(run_next_round_job, record_id)
    return job.id


def get_step_from_redis(record_id: int) -> Optional[str]:
    """供路由层读取 Redis 中暂存的当前步骤。"""
    try:
        conn = Redis.from_url(settings.redis_url, decode_responses=True)
        return conn.get(f"resume:task:{record_id}:step")
    except Exception:
        return None
