"""分析服务：运行 LangGraph 自动回环流水线并持久化到 DB。

单图自动回环：parser‖jd_analyst → advisor → rewriter → hr_qc
质检不通过且未达最大轮 → 回退 rewriter（携带 fix_instructions），最多 3 轮。

每完成一个节点更新 DB.current_step_name/current_step_desc/iteration_round + Redis step key。
Redis 缓存命中时跳过 LLM 调用并标记 cache_hit。
LLM 异常落库 error 状态 + failed_step，不静默崩溃。
"""

import logging
from datetime import datetime, timezone
from typing import Callable, Optional

from redis import Redis

from ..cache import cache_get_json, cache_set_json, make_cache_key
from ..config import get_settings
from ..db import SessionLocal
from ..models import AnalysisRecord, Iteration

logger = logging.getLogger("resume.service")

settings = get_settings()

_graph: Optional[Callable] = None

# 节点 → 动态文案映射
STEP_DESCRIPTIONS = {
    "resume_parser": "正在拆解你的简历，提取项目、技能、经历信息…",
    "jd_analyst": "正在解析岗位要求，区分硬性条件与加分项…",
    "baseline_qc": "正在对原始简历进行基线测评，便于优化前后对比…",
    "advisor": "正在对比简历与岗位，寻找能力差距…",
    "rewriter": "正在按照 XYZ/HR 阅读规则重写简历要点…",
    "hr_qc": "模拟 HR 进行五维度打分校验",
}

# 支持的工作模式
MODE_OPTIMIZE = "optimize"  # 选项一：直接优化后测评
MODE_COMPARE = "compare"    # 选项二：原始测评 → 优化 → 再测评

REWIND_DESC_PREFIX = "⚠️质检未通过，执行第 {n} 轮改写优化（共允许 3 轮）"


def _friendly_error(e: Exception) -> str:
    """将底层异常转换为用户可理解的中文提示，不暴露原始 JSON/堆栈。"""
    msg = str(e)
    low = msg.lower()
    if "502" in msg or "forward_failed" in msg or "上游连接失败" in msg:
        return "大模型服务暂时不可用（上游网关错误），请稍后重试。"
    if "timeout" in low or "timed out" in low or "10061" in msg:
        return "大模型响应超时，请检查网络或稍后重试。"
    if "connection" in low and ("refused" in low or "failed" in low):
        return "无法连接大模型服务，请确认本地代理（CC Switch）已启动。"
    if "rate" in low and "limit" in low:
        return "大模型调用频率超限，请稍后再试。"
    # 兜底：不泄露内部细节
    return "分析过程中出现异常，请稍后重试或联系管理员。"


def get_graph() -> Callable:
    global _graph
    if _graph is None:
        from .graph import build_graph
        _graph = build_graph()
    return _graph


# ---------------------------- 进度上报 ---------------------------- #

def _set_step(record_id: int, step_name: str, status: Optional[str] = None,
              step_desc: Optional[str] = None, iteration_round: Optional[int] = None) -> None:
    """更新 DB 步骤字段 + Redis step（供前端轮询）。"""
    desc = step_desc or STEP_DESCRIPTIONS.get(step_name, "")
    ts = datetime.now(timezone.utc).isoformat()
    try:
        conn = Redis.from_url(settings.redis_url, decode_responses=True)
        conn.set(f"resume:task:{record_id}:step", step_name, ex=7200)
        conn.set(f"resume:task:{record_id}:step_desc", desc, ex=7200)
        conn.set(f"resume:task:{record_id}:iteration_round", str(iteration_round or 0), ex=7200)
    except Exception as e:
        logger.warning("redis set step failed: %s", e)

    db = SessionLocal()
    try:
        rec = db.get(AnalysisRecord, record_id)
        if rec is not None:
            rec.current_step = step_name
            rec.current_step_name = step_name
            rec.current_step_desc = desc
            if iteration_round is not None:
                rec.iteration_round = iteration_round
            if status:
                rec.status = status
            db.commit()
    except Exception as e:
        logger.warning("db set step failed: %s", e)
    finally:
        db.close()


def _clear_step(record_id: int) -> None:
    try:
        conn = Redis.from_url(settings.redis_url, decode_responses=True)
        conn.delete(f"resume:task:{record_id}:step")
        conn.delete(f"resume:task:{record_id}:step_desc")
        conn.delete(f"resume:task:{record_id}:iteration_round")
    except Exception:
        pass


# ---------------------------- 缓存命中检查 ---------------------------- #

def _check_cache(record_id: int, resume_text: str, jd_text: str,
                 user_notes: str, target_position: str, mode: str) -> Optional[dict]:
    """检查相同输入+模式是否有缓存命中。命中则直接返回历史结果，跳过 LLM。"""
    key = make_cache_key(
        "analyze",
        resume_text=resume_text,
        jd_text=jd_text,
        user_notes=user_notes,
        target_position=target_position,
        mode=mode,
    )
    cached = cache_get_json(key, metadata={"record_id": record_id})
    if cached is None:
        return None
    logger.info("cache HIT for record_id=%s mode=%s, skipping LLM", record_id, mode)
    round_number = int(cached.get("round_number") or 1)
    # 把缓存结果落库（复用历史产物）
    db = SessionLocal()
    try:
        rec = db.get(AnalysisRecord, record_id)
        if rec is not None:
            rec.mode = mode
            rec.parsed_resume = cached.get("parsed_resume")
            rec.jd_analysis = cached.get("jd_analysis")
            rec.baseline_qc = cached.get("baseline_qc")
            rec.cache_hit = True
            # 写一轮 iteration（来自缓存）
            it = Iteration(
                record_id=record_id,
                round_number=round_number,
                optimization_advice=cached.get("optimization_advice"),
                rewritten_resume=cached.get("rewritten_resume"),
                final_qc=cached.get("final_qc"),
                qc_passed=cached.get("qc_passed"),
                fix_instructions=cached.get("fix_instructions"),
            )
            db.add(it)
            rec.current_round = round_number
            rec.iteration_round = round_number
            rec.current_step = None
            rec.current_step_name = None
            rec.current_step_desc = None
            rec.status = "done"
            db.commit()
    finally:
        db.close()
    _clear_step(record_id)
    return cached


def _write_cache(resume_text: str, jd_text: str, user_notes: str,
                 target_position: str, mode: str, result: dict) -> None:
    key = make_cache_key(
        "analyze",
        resume_text=resume_text,
        jd_text=jd_text,
        user_notes=user_notes,
        target_position=target_position,
        mode=mode,
    )
    cache_set_json(key, result, ttl=settings.cache_ttl)


# ---------------------------- 主流程 ---------------------------- #

def run_analysis(record_id: int) -> dict:
    """执行完整流水线（自动回环，最多 3 轮），写 DB + Redis。"""
    db = SessionLocal()
    try:
        rec = db.get(AnalysisRecord, record_id)
        if rec is None:
            return {"error": "record not found"}
        inputs = {
            "resume_text": rec.resume_text,
            "jd_text": rec.jd_text,
            "user_notes": rec.user_notes,
            "target_position": rec.target_position or "",
            "mode": rec.mode or MODE_OPTIMIZE,
        }
    finally:
        db.close()

    mode = inputs["mode"]

    # 1. 缓存命中检查（缓存按 mode 隔离，两种模式互不串用）
    cached = _check_cache(record_id, **inputs)
    if cached is not None:
        return {"cache_hit": True, "result": cached}

    # 2. 启动执行
    _set_step(record_id, "resume_parser", status="running", iteration_round=0)

    initial: dict = {
        **inputs,
        "parsed_resume": None,
        "jd_analysis": None,
        "optimization_advice": None,
        "rewritten_resume": None,
        "baseline_qc": None,
        "final_qc": None,
        "qc_passed": None,
        "qc_rounds": 0,
        "fix_instructions": None,
        "iteration_round": 0,
        "current_step_name": None,
        "current_step_desc": None,
        "step_timestamp": None,
        "cache_hit": False,
        "messages": [],
    }

    # 3. 以 stream 模式运行 graph，每完成一个节点更新进度
    state: dict = dict(initial)
    failed_step: Optional[str] = None
    try:
        for chunk in get_graph().stream(initial, stream_mode="updates"):
            for node_name, update in chunk.items():
                if isinstance(update, dict):
                    state.update(update)
                # optimize 模式下 baseline_qc 节点是纯 pass-through（无 LLM），
                # 不向前端暴露该步骤，避免步骤指示器闪烁
                if node_name == "baseline_qc" and mode != MODE_COMPARE:
                    continue
                # 回环改写时使用特殊文案
                round_num = state.get("iteration_round", 0) or 0
                if node_name == "rewriter" and round_num > 1:
                    desc = REWIND_DESC_PREFIX.format(n=round_num)
                else:
                    desc = STEP_DESCRIPTIONS.get(node_name, "")
                _set_step(
                    record_id,
                    node_name,
                    status="running",
                    step_desc=desc,
                    iteration_round=round_num,
                )
    except Exception as e:
        logger.exception("graph execution failed at step")
        friendly = _friendly_error(e)
        # 从 DB 读取当前执行步骤（_set_step 已实时写入），state 中不维护此字段
        failed_step = "unknown"
        db = SessionLocal()
        try:
            rec = db.get(AnalysisRecord, record_id)
            if rec is not None:
                failed_step = rec.current_step_name or rec.current_step or "unknown"
                rec.status = "error"
                rec.error = friendly
                rec.failed_step = failed_step
                rec.current_step = None
                rec.current_step_name = None
                rec.current_step_desc = None
                db.commit()
        finally:
            db.close()
        _clear_step(record_id)
        return {"error": friendly, "failed_step": failed_step}

    # 4. 持久化所有迭代轮次
    db = SessionLocal()
    try:
        rec = db.get(AnalysisRecord, record_id)
        if rec is None:
            return {"error": "record not found"}
        rec.parsed_resume = state.get("parsed_resume")
        rec.jd_analysis = state.get("jd_analysis")
        rec.mode = mode
        rec.baseline_qc = state.get("baseline_qc")
        rec.cache_hit = False

        # 图可能跑了多轮（rewriter 被多次执行），从 state 取最终产物
        final_round = state.get("iteration_round", 1) or 1
        rec.iteration_round = final_round
        rec.current_round = final_round

        it = Iteration(
            record_id=record_id,
            round_number=final_round,
            optimization_advice=state.get("optimization_advice"),
            rewritten_resume=state.get("rewritten_resume"),
            final_qc=state.get("final_qc"),
            qc_passed=state.get("qc_passed"),
            fix_instructions=state.get("fix_instructions"),
        )
        db.add(it)

        rec.current_step = None
        rec.current_step_name = None
        rec.current_step_desc = None
        rec.status = "done"
        db.commit()
    finally:
        db.close()

    _clear_step(record_id)

    result = {
        "mode": mode,
        "parsed_resume": state.get("parsed_resume"),
        "jd_analysis": state.get("jd_analysis"),
        "baseline_qc": state.get("baseline_qc"),
        "optimization_advice": state.get("optimization_advice"),
        "rewritten_resume": state.get("rewritten_resume"),
        "final_qc": state.get("final_qc"),
        "qc_passed": state.get("qc_passed"),
        "fix_instructions": state.get("fix_instructions"),
        "round_number": final_round,
    }

    # 5. 写入缓存（供相同输入命中）
    try:
        _write_cache(**inputs, result=result)
    except Exception as e:
        logger.warning("write cache failed: %s", e)

    return {"cache_hit": False, "result": result}
