"""LangGraph 多 Agent 编排图（自动回环 + 双工作模式）。

工作模式（state["mode"]）：
- optimize（选项一）：简历解析 ‖ JD 分析 → 顾问诊断 → 简历改写 → HR 质检
- compare（选项二）：简历解析 ‖ JD 分析 → 原始简历基线测评 → 顾问诊断 → 简历改写 → HR 质检
  基线测评节点在 optimize 模式下直接 pass-through（不产生 LLM 调用）。

质检不通过且未达最大轮次 → 回退改写（携带 fix_instructions），最多 3 轮。

单图 build_graph() 覆盖两种模式 + 首轮 + 所有迭代轮，无需拆分多个图。
"""

from typing import Callable

from langgraph.graph import END, START, StateGraph

from ..config import get_settings
from .advisor import resume_advisor_node
from .hr_qc import baseline_qc_node, hr_qc_node
from .jd_analyst import jd_analyst_node
from .resume_parser import resume_parser_node
from .rewriter import rewrite_node
from .state import AgentState

settings = get_settings()


def route_after_qc(state: AgentState) -> str:
    """质检后路由：通过 → END；未通过且未达最大轮 → 回退改写；达到最大轮 → END。"""
    passed = state.get("qc_passed")
    round_num = state.get("iteration_round", 0) or 0
    if passed:
        return "end"
    if round_num >= settings.max_qc_rounds:
        return "end"
    return "rewriter"


def build_graph() -> Callable:
    """构建完整流水线图（含基线测评 + 自动回环）。

    START → resume_parser ┐
    START → jd_analyst   ─┴→ baseline_qc → advisor → rewriter → hr_qc
    hr_qc → passed/round>=max ? END : rewriter

    baseline_qc 节点：compare 模式执行原始简历测评（1 次 LLM 调用），
    optimize 模式直接返回 {}，无额外开销。
    """
    g = StateGraph(AgentState)
    g.add_node("resume_parser", resume_parser_node)
    g.add_node("jd_analyst", jd_analyst_node)
    g.add_node("baseline_qc", baseline_qc_node)
    g.add_node("advisor", resume_advisor_node)
    g.add_node("rewriter", rewrite_node)
    g.add_node("hr_qc", hr_qc_node)

    g.add_edge(START, "resume_parser")
    g.add_edge(START, "jd_analyst")
    # fan-in：等解析与 JD 分析都完成后再进入基线测评（optimize 模式下该节点瞬时通过）
    g.add_edge("resume_parser", "baseline_qc")
    g.add_edge("jd_analyst", "baseline_qc")
    g.add_edge("baseline_qc", "advisor")
    g.add_edge("advisor", "rewriter")
    g.add_edge("rewriter", "hr_qc")
    g.add_conditional_edges("hr_qc", route_after_qc, {"rewriter": "rewriter", "end": END})
    return g.compile()
