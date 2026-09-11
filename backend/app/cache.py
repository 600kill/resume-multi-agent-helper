import json
from typing import Any, Optional

import redis

from .config import get_settings

settings = get_settings()

_redis: Optional[redis.Redis] = None


def get_redis() -> Optional[redis.Redis]:
    """获取 Redis 客户端单例，连接失败时返回 None（缓存降级为无）。"""
    global _redis
    if _redis is None:
        try:
            _redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)
            _redis.ping()
        except Exception:
            _redis = None
    return _redis


def cache_get(key: str) -> Optional[str]:
    r = get_redis()
    if r is None:
        return None
    try:
        return r.get(key)
    except Exception:
        return None


def cache_set(key: str, value: str, ttl: int | None = None) -> None:
    r = get_redis()
    if r is None:
        return
    try:
        r.set(key, value, ex=ttl or settings.cache_ttl)
    except Exception:
        pass


def cache_get_json(key: str) -> Optional[Any]:
    raw = cache_get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def cache_set_json(key: str, value: Any, ttl: int | None = None) -> None:
    cache_set(key, json.dumps(value, ensure_ascii=False), ttl=ttl)


def cache_key(*parts: str) -> str:
    return "resume:" + ":".join(map(str, parts))