from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置：从环境变量读取，默认值适配本地沙箱预览。"""

    app_name: str = "简历多智能体优化助手"
    version: str = "0.1.0"

    # LLM（OpenAI 兼容端点；本地经 CC Switch / Codex 客户端转发）
    model: str = "glm-4.6v"
    llm_base_url: str = "http://127.0.0.1:15721/v1"
    llm_api_key: str = "ccswitch-local"  # 本地代理不鉴权，占位即可
    llm_timeout: int = 180
    llm_max_tokens: int = 8192

    # PostgreSQL
    database_url: str = "postgresql://resume:resume@127.0.0.1:5432/resume_agent"

    # Redis
    redis_url: str = "redis://127.0.0.1:6379/0"
    cache_ttl: int = 3600  # 分析结果缓存 1 小时

    # HR 质检最大迭代轮次（改写次数上限，防止死循环）
    max_qc_rounds: int = 3

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="RESUME_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()