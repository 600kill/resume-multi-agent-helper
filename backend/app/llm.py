import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from coze_coding_dev_sdk import LLMClient
from coze_coding_utils.runtime_ctx.context import Context, new_context

from .config import get_settings

settings = get_settings()
_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _client
    if _client is None:
        ctx: Context = new_context(method="invoke")
        _client = LLMClient(ctx=ctx)
    return _client


def _get_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        if content and isinstance(content[0], str):
            return " ".join(content)
        return " ".join(
            item.get("text", "")
            for item in content
            if isinstance(item, dict) and item.get("type") == "text"
        )
    return str(content)


def ask(system_prompt: str, user_content: str, temperature: float = 0.3) -> str:
    """调用 LLM，返回纯文本响应。"""
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]
    resp = get_llm_client().invoke(
        messages=messages,
        model=settings.model,
        temperature=temperature,
        max_completion_tokens=8192,
    )
    return _get_text(resp.content).strip()


def ask_json(system_prompt: str, user_content: str, temperature: float = 0.2) -> dict:
    """调用 LLM 并要求返回合法 JSON 对象，失败时返回空 dict。"""
    inner_system = system_prompt + (
        "\n\n你必须只输出一个合法 JSON 对象，不要包含任何 Markdown 代码块标记、"
        "不要有多余文字或注释。"
    )
    raw = ask(inner_system, user_content, temperature=temperature)
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    # 尝试提取 JSON 片段
    try:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            data = json.loads(raw[start : end + 1])
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}