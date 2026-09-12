"""Agent 5: 模拟 HR 质检员 —— 对改写后的简历做质量与岗位匹配度质检。

质检未通过时打回给改写员迭代，直到达标或达到最大轮次。
"""

import json

from ..llm import ask_json
from .state import AgentState


SYSTEM_PROMPT = """你是一名严格的模拟 HR 质检员和简历筛选专家。请对改写后的简历进行质检打分。

评估维度及满分如下：
- match_score: 与目标岗位 JD 的匹配度（0-100）
- keyword_score: 岗位关键词覆盖度（0-100）
- impact_score: 成果表达力/是否有量化与 STAR（0-100）
- clarity_score: 结构清晰、语言专业（0-100）
- authenticity_score: 真实性，是否疑似编造经历（0-100）

请按以下 JSON 结构输出：
{
  "scores": {
    "match_score": 0,
    "keyword_score": 0,
    "impact_score": 0,
    "clarity_score": 0,
    "authenticity_score": 0
  },
  "overall_score": 0,
  "passed": true,
  "strengths": ["做得好的地方"],
  "weaknesses": ["仍存在的问题，逐条列出"],
  "fix_instructions": ["若未通过，需要改写员具体修改的问题及修改要求"],
  "comments": "整体质检意见"
}

判定规则：当 authenticity_score 低于 80（疑似编造）或 overall_score 低于 75 时 passed 为 false，
否则为 true。overall_score 为各维度加权后的综合分。"""


def build_prompt(state: AgentState, round_num: int) -> str:
    jd = json.dumps(state["jd_analysis"] or {}, ensure_ascii=False, indent=2)
    fixes = state.get("fix_instructions") or []
    if fixes:
        # 迭代轮：明确告知上一轮质检提出的修改要求，便于核对本轮是否落实
        req_lines = "\n".join(f"{i}. {item}" for i, item in enumerate(fixes, 1))
        requirements = f"上一轮质检提出的修改要求如下，请核对改写稿是否逐条落实：\n{req_lines}"
    else:
        # 首轮质检：保持原行为，使用顾问的优化建议
        requirements = json.dumps(state["optimization_advice"] or {}, ensure_ascii=False, indent=2)
    if state.get("rewritten_resume"):
        extra = f'''==== 待质检的改写后简历 ====\n{state["rewritten_resume"]}'''
    else:
        extra = "==== 待质检的简历 ====\n" + state["resume_text"]
    return f"""这是第 {round_num} 轮质检。请对以下简历做质检打分：

==== 目标岗位 JD 分析 ====
{jd}

==== 本轮优化要求（上一轮质检给出的修改指令） ====
{requirements}

{extra}

请输出结构化 JSON。"""


def hr_qc_node(state: AgentState) -> dict:
    # 轮次以改写节点维护的 iteration_round 为准（每次改写后已 +1）
    round_num = state.get("iteration_round", 0) or state.get("qc_rounds", 0) or 1
    prompt = build_prompt(state, round_num)
    qc = ask_json(SYSTEM_PROMPT, prompt, temperature=0.2)
    passed = bool(qc.get("passed"))
    fix_instructions = qc.get("fix_instructions") or []
    if not isinstance(fix_instructions, list):
        fix_instructions = [str(fix_instructions)]
    return {
        "final_qc": qc,
        "qc_passed": passed,
        "qc_rounds": round_num,
        "iteration_round": round_num,
        "fix_instructions": fix_instructions,
    }