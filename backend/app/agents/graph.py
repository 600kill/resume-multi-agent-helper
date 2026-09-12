"""LangGraph 多 Agent 编排图。

两种执行模式（移除自动回环，每轮 QC 后停止，由人工 /iterate 接口触发下一轮）：

1. 首轮图 build_graph()：
   START → 简历解析者 ┐
   START → JD 分析师 ┘→ 求职简历顾问 → 简历改写员 → 模拟HR质检员 → END

2. 迭代轮图 build_iteration_graph()：
   START → 求职简历顾问 → 简历改写员 → 模拟HR质检员 → END

   （基于上轮 fix_instructions + 首轮 parsed_resume/jd_analysis 再跑一轮）
"""

from typing import Callable

from langgraph.graph import END, START, StateGraph

from .advisor import resume_advisor_node
from .hr_qc import hr_qc_node
from .jd_analyst import jd_analyst_node
from .resume_parser import resume_parser_node
from .rewriter import rewrite_node
from .state import AgentState


def build_graph() -> Callable:
    """首轮图：5 个 Agent 全跑一遍后停止。"""
    g = StateGraph(AgentState)
    g.add_node("resume_parser", resume_parser_node)
    g.add_node("jd_analyst", jd_analyst_node)
    g.add_node("advisor", resume_advisor_node)
    g.add_node("rewriter", rewrite_node)
    g.add_node("hr_qc", hr_qc_node)

    g.add_edge(START, "resume_parser")
    g.add_edge(START, "jd_analyst")
    g.add_edge("resume_parser", "advisor")
    g.add_edge("jd_analyst", "advisor")
    g.add_edge("advisor", "rewriter")
    g.add_edge("rewriter", "hr_qc")
    g.add_edge("hr_qc", END)
    return g.compile()


def build_iteration_graph() -> Callable:
    """迭代轮图：仅 advisor→rewriter→hr_qc 三节点。

    初始 state 由调用方提供：parsed_resume、jd_analysis、fix_instructions、
    iteration_round（=本轮轮次，如 2、3）。
    """
    g = StateGraph(AgentState)
    g.add_node("advisor", resume_advisor_node)
    g.add_node("rewriter", rewrite_node)
    g.add_node("hr_qc", hr_qc_node)

    g.add_edge(START, "advisor")
    g.add_edge("advisor", "rewriter")
    g.add_edge("rewriter", "hr_qc")
    g.add_edge("hr_qc", END)
    return g.compile()
