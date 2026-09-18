"""Agent 3: 求职简历顾问 —— 结合简历结构化信息 + JD 三级报告 + 用户建议，产出差距诊断与逐条修改建议。"""

import json

from ..llm import ask_json
from .state import AgentState


SYSTEM_PROMPT = """你是简历诊断顾问Agent。规则：
1. 对比解析简历与JD三级报告，诊断Must-Have证据缺口、未充分利用的Should-Have素材。
2. 给出可执行修改建议，写明修改位置、方向，仅使用简历已有事实，禁止虚构。
3. 用XYZ评估项目，标记弱动词、缺失量化点。
输出差距诊断+逐条修改建议。

JSON结构：
{
  "gap_analysis": {
    "must_have_gaps": ["Must-Have 证据缺口（简历未覆盖的硬性要求）"],
    "should_have_underutilized": ["Should-Have 素材未充分利用的地方"],
    "matched_points": ["简历与岗位匹配的亮点"]
  },
  "xyz_evaluation": [
    {
      "project": "项目名称",
      "x": "做了什么（X）",
      "y": "范围/条件（Y）",
      "z": "结果指标（Z，缺失则标注'缺失量化点'）",
      "weak_verbs": ["弱动词列表"],
      "missing_quantification": ["缺失的量化点"]
    }
  ],
  "improvement_suggestions": [
    {
      "section": "修改位置（如：项目经历/技能/个人简介）",
      "issue": "当前存在的问题",
      "direction": "修改方向",
      "suggestion": "具体建议"
    }
  ],
  "keyword_recommendations": ["建议补充/强化的岗位关键词"],
  "overall_advice": "总体优化重点的一句话总结"
}"""


def build_prompt(state: AgentState) -> str:
    parsed = json.dumps(state["parsed_resume"] or {}, ensure_ascii=False, indent=2)
    jd = json.dumps(state["jd_analysis"] or {}, ensure_ascii=False, indent=2)
    notes = (state.get("user_notes") or "").strip() or "无"
    return f"""请基于以下信息给出简历优化建议：

==== 求职者简历（结构化提取） ====
{parsed}

==== 目标岗位 JD 分析（三级分类） ====
{jd}

==== 求职者本人补充建议 ====
{notes}

请输出结构化 JSON。"""


def resume_advisor_node(state: AgentState) -> dict:
    prompt = build_prompt(state)
    advice = ask_json(SYSTEM_PROMPT, prompt)
    return {"optimization_advice": advice}
