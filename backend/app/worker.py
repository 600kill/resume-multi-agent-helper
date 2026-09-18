"""RQ 任务队列：入队接口 + Worker 执行的 job 函数。

Worker 进程消费 "resume" 队列，调用 service.run_analysis 执行完整流水线
（含自动回环），并把进度写入 Redis 与 DB。
"""

import logging
from typing import Optional

from redis import Redis
from rq import Queue

from .agents.service import _friendly_error, run_analysis
from .config import get_settings
from .db import SessionLocal
from .models import AnalysisRecord

logger = logging.getLogger("resume.worker")

settings = get_settings()


def get_queue() -> Queue:
    """获取 RQ 队列单例（连接 Redis）。

    RQ 内部期望 bytes，不能 decode_responses=True。
    """
    conn = Redis.from_url(settings.redis_url, decode_responses=False)
    return Queue("resume", connection=conn)


def run_analysis_job(record_id: int) -> dict:
    """Worker 执行：完整流水线（自动回环，最多 3 轮）。"""
    try:
        return run_analysis(record_id=record_id)
    except Exception as e:
        logger.exception("analysis job failed")
        friendly = _friendly_error(e)
        db = SessionLocal()
        try:
            rec = db.get(AnalysisRecord, record_id)
            if rec is not None:
                rec.status = "error"
                rec.error = friendly
                rec.failed_step = rec.current_step_name or "unknown"
                rec.current_step = None
                rec.current_step_name = None
                rec.current_step_desc = None
                db.commit()
        finally:
            db.close()
        return {"error": friendly}


def enqueue_analysis(record_id: int) -> str:
    """入队分析任务，返回 RQ job id。"""
    job = get_queue().enqueue(run_analysis_job, record_id)
    return job.id


def get_step_from_redis(record_id: int) -> Optional[dict]:
    """供路由层读取 Redis 中暂存的当前步骤信息。"""
    try:
        conn = Redis.from_url(settings.redis_url, decode_responses=True)
        step = conn.get(f"resume:task:{record_id}:step")
        desc = conn.get(f"resume:task:{record_id}:step_desc")
        round_str = conn.get(f"resume:task:{record_id}:iteration_round")
        return {
            "step": step,
            "desc": desc,
            "iteration_round": int(round_str) if round_str else 0,
        }
    except Exception:
        return None
