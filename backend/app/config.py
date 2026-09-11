from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置：从环境变量读取，默认值适配本地沙箱预览。"""

    app_name: str = "简历多智能体优化助手"
    version: str = "0.1.0"

    # LLM
    model: str = "doubao-seed-2-0-pro-260215"

    # PostgreSQL
    database_url: str = "postgresql://resume:resume@127.0.0.1:5432/resume_agent"

    # Redis
    redis_url: str = "redis://127.0.0.1:6379/0"
    cache_ttl: int = 3600  # 分析结果缓存 1 小时

    # HR 质检最大迭代轮次
    max_qc_rounds: int = 2

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="RESUME_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()