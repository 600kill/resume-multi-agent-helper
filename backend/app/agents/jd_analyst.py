"""Agent 2: JD 分析师 —— 分析岗位 JD，按三级分类提炼核心要求。"""

from ..llm import ask_json
from .state import AgentState


SYSTEM_PROMPT = """你是JD解析Agent。规则：
1. 把JD拆解三级：Must-Have(硬性门槛) / Should-Have(期望能力) / Nice-to-Have(加分项)。
2. 每条同时提取关键词+岗位行为描述，区分工具要求和业务任务。
输出结构化三级分类报告。

JSON结构：
{
  "must_have": [
    {"keyword": "关键词", "behavior": "岗位行为描述", "type": "tool|business", "raw": "JD原文片段"}
  ],
  "should_have": [
    {"keyword": "关键词", "behavior": "岗位行为描述", "type": "tool|business", "raw": "JD原文片段"}
  ],
  "nice_to_have": [
    {"keyword": "关键词", "behavior": "岗位行为描述", "type": "tool|business", "raw": "JD原文片段"}
  ],
  "keywords": ["所有关键词汇总"],
  "ideal_candidate_profile": "理想候选人一句话画像"
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
