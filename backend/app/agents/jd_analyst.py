"""Agent 2: JD 分析师 —— 分析岗位 JD，提炼核心要求与筛选关键词。"""

from ..llm import ask_json
from .state import AgentState


SYSTEM_PROMPT = """你是一名资深人力资源分析师，擅长拆解岗位 JD（职位描述）。

请按以下 JSON 结构输出 JD 分析结果：
{
  "hard_requirements": ["硬性要求，如学历、年限、特定技术"],
  "soft_skills": ["软性能力，如沟通、协作、抗压"],
  "technical_skills": ["具体要求的技术栈/工具"],
  "responsibilities": ["主要工作职责"],
  "keywords": ["JD 中出现、招聘系统/HR 会用于筛选的关键词"],
  "ideal_candidate_profile": "理想候选人的一句话画像"
}"""


def build_prompt(state: AgentState) -> str:
    jd = state["jd_text"].strip()
    if not jd:
        return "本次没有提供 JD。请基于通用的该岗位要求做一个合理默认假设，并如实标注'未提供 JD，以下为通用要求'。"
    return f"""请分析以下岗位 JD：

==== JD 原文 ====
{jd}
==== JD 结束 ====

请输出结构化 JSON。"""


def jd_analyst_node(state: AgentState) -> dict:
    prompt = build_prompt(state)
    analysis = ask_json(SYSTEM_PROMPT, prompt)
    return {"jd_analysis": analysis}