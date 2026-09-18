from typing import Annotated, Optional, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """LangGraph 多 Agent 流水线的共享状态。"""

    # 输入
    resume_text: str
    jd_text: str
    user_notes: str
    target_position: str
    # 工作模式：optimize=直接优化后测评（选项一）；compare=先测评原始简历→优化→再测评（选项二）
    mode: str

    # 各阶段产物
    parsed_resume: Optional[dict]
    jd_analysis: Optional[dict]
    optimization_advice: Optional[dict]
    rewritten_resume: Optional[str]

    # compare 模式：优化前对原始简历的基线测评结果（optimize 模式为 None）
    baseline_qc: Optional[dict]

    # HR 质检
    final_qc: Optional[dict]
    qc_passed: Optional[bool]
    qc_rounds: int

    # 质检打回改写：上一轮 HR 给出的具体修改指令 + 当前改写迭代轮次（0=尚未改写）
    fix_instructions: Optional[list]
    iteration_round: int

    # 步骤进度（供前端展示，每个节点执行时更新）
    current_step_name: Optional[str]       # 节点名：resume_parser/jd_analyst/advisor/rewriter/hr_qc
    current_step_desc: Optional[str]       # 动态文案
    step_timestamp: Optional[str]          # 步骤开始时间 ISO8601

    # 缓存命中标记
    cache_hit: Optional[bool]

    # 运行消息（用于进度回调）
    messages: Annotated[list, add_messages]
