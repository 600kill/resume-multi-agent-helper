"""LangGraph 多 Agent 编排图。

流水线：
  简历解析者 -> JD 分析师（并行） -> 求职简历顾问 -> 简历改写员 -> 模拟HR质检员
                                                    ^                 |
                                                    |__未通过则打回____|（最多 max_qc_rounds 轮）
"""

from typing import Callable

from langgraph.graph import END, START, StateGraph

from ..config import get_settings
from .advisor import resume_advisor_node
from .hr_qc import hr_qc_node
from .jd_analyst import jd_analyst_node
from .resume_parser import resume_parser_node
from .rewriter import rewrite_node
from .state import AgentState

settings = get_settings()


def route_after_qc(state: AgentState) -> str:
    """质检未通过且未超轮次 -> 打回改写员；否则结束。"""
    passed = state.get("qc_passed")
    rounds = state.get("qc_rounds", 0)
    if not passed and rounds < settings.max_qc_rounds:
        return "rewriter"
    return "end"


def build_graph() -> Callable:
    g = StateGraph(AgentState)

    # 节点
    g.add_node("resume_parser", resume_parser_node)
    g.add_node("jd_analyst", jd_analyst_node)
    g.add_node("advisor", resume_advisor_node)
    g.add_node("rewriter", rewrite_node)
    g.add_node("hr_qc", hr_qc_node)

    # 入口：解析 与 JD 分析并行
    g.add_edge(START, "resume_parser")
    g.add_edge(START, "jd_analyst")
    g.add_edge("resume_parser", "advisor")
    g.add_edge("jd_analyst", "advisor")
    g.add_edge("advisor", "rewriter")
    g.add_edge("rewriter", "hr_qc")

    # 条件边：质检
    g.add_conditional_edges(
        "hr_qc",
        route_after_qc,
        {"rewriter": "rewriter", "end": END},
    )

    graph = g.compile()
    return graph