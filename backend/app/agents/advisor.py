"""Agent 3: 求职简历顾问 —— 结合简历结构化信息 + JD 要求 + 用户建议，产出问题清单与优化方向。"""

import json

from ..llm import ask_json
from .state import AgentState


SYSTEM_PROMPT = """你是一名资深求职简历顾问，专门帮助求职者把简历改到能通过 HR 筛选、打动技术面试官。

请结合三者：求职者简历的结构化信息、目标岗位 JD 分析、求职者本人的补充建议，
诊断当前简历与目标岗位的差距，并输出优化建议。

请严格按以下 JSON 结构输出：
{
  "gap_analysis": {
    "matched_points": ["简历与岗位匹配的亮点"],
    "mismatches": ["不符合岗位要求或存在差距的地方"]
  },
  "keyword_recommendations": ["建议补充/强化的岗位关键词"],
  "improvement_suggestions": [
    {
      "section": "需要优化的板块（如：项目经历 / 技能 / 个人简介）",
      "issue": "当前存在的问题",
      "suggestion": "如何改进的具体建议"
    }
  ],
  "skill_gaps": ["建议求职者补充或强调的技能"],
  "overall_advice": "总体优化重点的一句话总结"
}"""


def build_prompt(state: AgentState) -> str:
    parsed = json.dumps(state["parsed_resume"] or {}, ensure_ascii=False, indent=2)
    jd = json.dumps(state["jd_analysis"] or {}, ensure_ascii=False, indent=2)
    notes = (state.get("user_notes") or "").strip() or "无"
    return f"""请基于以下信息给出简历优化建议：

==== 求职者简历（结构化提取） ====
{parsed}

==== 目标岗位 JD 分析 ====
{jd}

==== 求职者本人补充建议 ====
{notes}

请输出结构化 JSON。"""


def resume_advisor_node(state: AgentState) -> dict:
    prompt = build_prompt(state)
    advice = ask_json(SYSTEM_PROMPT, prompt)
    return {"optimization_advice": advice}