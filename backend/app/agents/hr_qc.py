"""Agent 5: HR 质检员 —— 五维度打分（带证据溯源），未通过时输出 fix_instructions 打回改写。

五维权重：JD匹配度35 / 内容证据质量25 / 真实性边界15 / ATS友好性15 / 可读性10，总分100。
"""

import json

from ..llm import ask_json
from .state import AgentState


SYSTEM_PROMPT = """你是HR质检Agent，打分必须带证据溯源，禁止主观臆断。
总分100五维度：
1.JD匹配度35分；2.内容证据质量25分；3.真实性边界15分；4.ATS友好性15分；5.可读性10分。
流程：
1.逐项打分，每项引用简历原文作为证据。
2.输出fix_instructions明确写出修改点，用于打回改写。
3.判定：通过/不通过，达最大迭代轮直接结束。
输出：五维评分、是否通过标记、fix_instructions清单。

JSON结构：
{
  "scores": {
    "jd_match": 0,
    "evidence_quality": 0,
    "authenticity": 0,
    "ats_friendly": 0,
    "readability": 0
  },
  "weights": {"jd_match": 35, "evidence_quality": 25, "authenticity": 15, "ats_friendly": 15, "readability": 10},
  "overall_score": 0,
  "passed": true,
  "evidence": [
    {"dimension": "维度名", "score": 0, "evidence": "引用简历原文作为证据", "reason": "打分理由"}
  ],
  "strengths": ["做得好的地方"],
  "weaknesses": ["仍存在的问题，逐条列出"],
  "fix_instructions": ["若未通过，需要改写员具体修改的问题及修改要求"],
  "comments": "整体质检意见"
}

判定规则：overall_score >= 75 且 authenticity >= 12 时 passed=true，否则 false。
overall_score = 各维度得分（已按权重折算，如jd_match得分/35*35）的总和。"""


def build_prompt(state: AgentState, round_num: int) -> str:
    jd = json.dumps(state["jd_analysis"] or {}, ensure_ascii=False, indent=2)
    fixes = state.get("fix_instructions") or []
    if fixes:
        req_lines = "\n".join(f"{i}. {item}" for i, item in enumerate(fixes, 1))
        requirements = f"上一轮质检提出的修改要求如下，请核对改写稿是否逐条落实：\n{req_lines}"
    else:
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


# ---------------------------- 基线测评（compare 模式专用） ---------------------------- #

BASELINE_PROMPT_NOTE = (
    "注意：这是优化前的【原始简历】基线测评，目的是与后续优化稿做分数对比。"
    "请严格按同一套五维标准客观打分，如实指出原始简历存在的问题，"
    "不要因为简历尚未优化而刻意打高或打低。"
)


def build_baseline_prompt(state: AgentState) -> str:
    """对原始简历做基线测评的 prompt（compare 模式，在顾问/改写之前执行）。"""
    jd = json.dumps(state.get("jd_analysis") or {}, ensure_ascii=False, indent=2)
    return f"""这是优化前的原始简历基线测评（用于优化前后对比）。请对以下原始简历做质检打分：

==== 目标岗位 JD 分析 ====
{jd}

==== 待测评的原始简历（未经任何优化） ====
{state.get("resume_text", "")}

{BASELINE_PROMPT_NOTE}
请输出结构化 JSON。"""


def baseline_qc_node(state: AgentState) -> dict:
    """compare 模式：优化前先测评原始简历；optimize 模式直接跳过（不产生 LLM 调用）。"""
    if state.get("mode") != "compare":
        return {}
    qc = ask_json(SYSTEM_PROMPT, build_baseline_prompt(state), temperature=0.2)
    # 防御式兜底：保证返回结构永远是 dict
    if not isinstance(qc, dict):
        qc = {}
    qc["is_baseline"] = True
    return {"baseline_qc": qc}
