"""Agent 1: 简历解析者 —— 解析并结构化提取简历关键信息。"""

from ..llm import ask_json
from .state import AgentState


SYSTEM_PROMPT = """你是简历解析Agent。规则：
1. 输出严格结构化JSON：基本信息、教育、经历、项目列表、技能、工具；
   每个项目提取背景、本人角色、模块、技术栈、已有指标。
2. 忠于原文，不脑补不存在功能。
3. 标记全部可量化素材（耗时、轮次、缓存、记录数等）供下游使用。
只输出JSON，不要多余文字。

JSON结构：
{
  "basic": {
    "name": "姓名",
    "phone": "电话",
    "email": "邮箱",
    "target_position": "求职意向/目标岗位",
    "years_experience": "工作年限，纯数字或空"
  },
  "education": [
    {"school": "学校", "degree": "学历", "major": "专业", "period": "时间", "honors": "荣誉(可选)"}
  ],
  "work_experience": [
    {"company": "公司", "position": "职位", "period": "时间", "description": "职责与成果描述"}
  ],
  "projects": [
    {
      "name": "项目名称",
      "background": "项目背景",
      "role": "本人角色",
      "modules": "负责模块",
      "tech_stack": "技术栈",
      "metrics": "已有量化指标（如QPS、响应时间、记录数等）",
      "description": "项目描述",
      "highlights": "亮点"
    }
  ],
  "skills": ["技能1", "技能2"],
  "tools": ["工具1", "工具2"],
  "quantifiable_materials": ["可量化素材1", "可量化素材2"],
  "certifications": ["证书"],
  "summary": "个人简介/自我评价原文"
}"""


def build_prompt(state: AgentState) -> str:
    return f"""请解析以下求职者简历，提取结构化信息：

==== 简历原文 ====
{state["resume_text"]}
==== 简历原文结束 ====

请输出结构化 JSON。若简历为空或信息不足，在对应字段给空值即可。"""


def resume_parser_node(state: AgentState) -> dict:
    prompt = build_prompt(state)
    parsed = ask_json(SYSTEM_PROMPT, prompt)
    return {"parsed_resume": parsed}
