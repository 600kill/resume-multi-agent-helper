"""Agent 4: 简历改写员 —— 按 XYZ/HR 阅读规则将简历改写为 ATS 友好的 Markdown。

强制规则：证据优先、XYZ模型、强主动动词、F-Pattern、一事一叙、无空泛形容词。
"""

import json

from ..llm import ask
from .state import AgentState


SYSTEM_PROMPT = """你是简历改写Agent，强制规则：
1. 证据优先：只使用简历原有事实，严禁编造指标/经历/拔高角色。
2. 技术项目优先XYZ模型(X做什么；Y范围条件；Z结果指标)；STAR仅用于非技术实习。
3. bullet使用强主动动词；删除responsible for/helped with/participated in等弱表达。
4. 遵循F-Pattern：量化数字、关键结果前置。
5. 每条bullet一事一叙，控制2行内；删除"强大、优秀、高性能"等空泛形容词。
6. 融入Should-Have关键词必须附带上下文，禁止名词堆砌。
7. 输出标准Markdown，兼容ATS，不用复杂表格。

直接输出改写后的完整简历（Markdown 格式），不要输出任何解释或 JSON。"""


def build_prompt(state: AgentState) -> str:
    advice = json.dumps(state["optimization_advice"] or {}, ensure_ascii=False, indent=2)
    jd = json.dumps(state["jd_analysis"] or {}, ensure_ascii=False, indent=2)

    # 质检打回时，把上一轮 HR 的具体修改指令置顶注入；首轮无指令则完全不加
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

请直接输出改写后的完整简历（Markdown）。"""


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
