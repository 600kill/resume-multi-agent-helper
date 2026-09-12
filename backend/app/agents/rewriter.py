"""Agent 4: 简历改写员 —— 按优化建议将求职者简历改写为面向目标岗位的优化版本。

改写遵循 STAR 法则（情境-任务-行动-结果），强调量化成果与岗位关键词，
同时保留求职者信息的真实性，不编造经历。
"""

import json

from ..llm import ask
from .state import AgentState


SYSTEM_PROMPT = """你是一名专业的 AI 简历改写专家。请基于求职者的原简历、JD 分析结果和优化建议，
将简历改写为一份针对目标岗位的高质量优化版简历。

改写要求：
1. 只基于原简历中已有的真实信息进行表达优化，绝不编造不存在的经历、技能或数据。
2. 项目经历和职责描述尽量用 STAR 法则组织，突出行动和可量化的结果（若原简历有数字就保留并强化）。
3. 自然地融入目标岗位 JD 中的关键技能关键词，但不能生硬堆砌。
4. 结构清晰：个人信息 / 个人简介 / 技能 / 教育背景 / 项目与工作经历 / 证书（如有）。
5. 语言精炼、专业，符合中文简历规范。

直接输出改写后的完整简历文本（Markdown 格式），不要输出任何解释或 JSON。"""


def build_prompt(state: AgentState) -> str:
    advice = json.dumps(state["optimization_advice"] or {}, ensure_ascii=False, indent=2)
    jd = json.dumps(state["jd_analysis"] or {}, ensure_ascii=False, indent=2)

    # 质检打回时，把上一轮 HR 的具体修改指令置顶注入；首轮无指令则完全不加，保持原 prompt
    fixes = state.get("fix_instructions") or []
    fix_block = ""
    if fixes:
        lines = "\n".join(f"{i}. {item}" for i, item in enumerate(fixes, 1))
        round_num = state.get("iteration_round", 0)
        fix_block = (
            f"\n==== 上一轮质检未通过，请逐条落实以下修改要求（第 {round_num} 轮改写）====\n"
            f"{lines}\n"
        )

    return f"""==== 求职者原简历 ====
{state["resume_text"]}

==== 目标岗位 JD 分析 ====
{jd}
{fix_block}
==== 优化建议 ====
{advice}

请直接输出改写后的完整简历。"""


def _strip_code_fence(text: str) -> str:
    """模型偶尔会用 ```markdown ... ``` 包裹输出，剥掉围栏只留正文。"""
    t = text.strip()
    if t.startswith("```"):
        first_nl = t.find("\n")
        t = t[first_nl + 1 :] if first_nl != -1 else t[3:]
    if t.rstrip().endswith("```"):
        t = t.rstrip()[:-3]
    return t.strip()


def rewrite_node(state: AgentState) -> dict:
    iteration_round = state.get("iteration_round", 0) + 1
    state = {**state, "iteration_round": iteration_round}
    prompt = build_prompt(state)
    rewritten = _strip_code_fence(ask(SYSTEM_PROMPT, prompt, temperature=0.6))
    return {"rewritten_resume": rewritten, "iteration_round": iteration_round}