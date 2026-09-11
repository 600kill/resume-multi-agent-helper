from typing import Annotated, Optional, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """LangGraph 多 Agent 流水线的共享状态。"""

    # 输入
    resume_text: str
    jd_text: str
    user_notes: str
    target_position: str

    # 各阶段产物
    parsed_resume: Optional[dict]
    jd_analysis: Optional[dict]
    optimization_advice: Optional[dict]
    rewritten_resume: Optional[str]

    # HR 质检
    final_qc: Optional[dict]
    qc_passed: Optional[bool]
    qc_rounds: int

    # 运行消息（用于进度回调）
    messages: Annotated[list, add_messages]