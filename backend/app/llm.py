"""LLM 调用封装：对接 OpenAI 兼容端点（本地经 CC Switch / Codex 客户端转发）。

对上层只暴露 ask / ask_json 两个函数，5 个 Agent 与 LangGraph 编排
不感知具体模型与协议。
"""

import json

from openai import OpenAI

from .config import get_settings

settings = get_settings()
_client: OpenAI | None = None


def get_llm_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            timeout=settings.llm_timeout,
        )
    return _client


def ask(system_prompt: str, user_content: str, temperature: float = 0.3) -> str:
    """调用 LLM，返回纯文本响应。"""
    resp = get_llm_client().chat.completions.create(
        model=settings.model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        temperature=temperature,
        max_tokens=settings.llm_max_tokens,
    )
    return (resp.choices[0].message.content or "").strip()


_JSON_ONLY_SUFFIX = (
    "\n\n你必须只输出一个合法 JSON 对象，不要包含任何 Markdown 代码块标记、"
    "不要有多余文字或注释。"
)


def _parse_json_object(raw: str) -> dict | None:
    """尽力从模型输出中解析出 JSON 对象，失败返回 None。"""
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    # 尝试提取 {...} 片段（模型可能带了解释性文字或代码块）
    try:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            data = json.loads(raw[start : end + 1])
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return None


def ask_json(system_prompt: str, user_content: str, temperature: float = 0.2) -> dict:
    """调用 LLM 并要求返回合法 JSON 对象。

    解析失败时带原输出纠错重试一次；仍失败返回空 dict。
    """
    raw = ask(system_prompt + _JSON_ONLY_SUFFIX, user_content, temperature=temperature)
    data = _parse_json_object(raw)
    if data is not None:
        return data

    # 纠错重试：把模型自己的非法输出回传，要求修正
    fix_prompt = (
        "你上一次的输出不是合法 JSON（要求键和字符串值必须用双引号）：\n"
        f"{raw[:2000]}\n\n"
        "请只输出修正后的合法 JSON 对象，不要包含任何其他内容或 Markdown 标记。"
    )
    try:
        fixed = ask(system_prompt + _JSON_ONLY_SUFFIX, fix_prompt, temperature=0.0)
    except Exception:
        return {}
    return _parse_json_object(fixed) or {}
