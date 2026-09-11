"""Agent 1: 简历解析者 —— 解析并结构化提取简历关键信息。"""

from ..llm import ask_json
from .state import AgentState


SYSTEM_PROMPT = """你是一名资深简历解析专家。请从求职者简历中提取结构化的关键信息。

请严格按照以下 JSON 结构输出，缺失的信息用空字符串或空列表表示：
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
    {"name": "项目名称", "role": "角色", "tech_stack": "技术栈", "description": "项目描述", "highlights": "亮点/量化成果"}
  ],
  "skills": ["技能1", "技能2"],
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