import hashlib
import json
import logging
from typing import Any, Optional

import redis

from .config import get_settings

logger = logging.getLogger("resume.cache")
# 保证本地直跑（无 uvicorn 日志配置）时命中/未命中日志也可见
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger.addHandler(_h)
    logger.setLevel(logging.INFO)
    logger.propagate = False  # 自带 handler，避免 uvicorn root 下重复打印

settings = get_settings()

_redis: Optional[redis.Redis] = None

# 缓存 key 版本前缀：结构不兼容调整时升版（v1 → v2）即可使旧缓存自然失效
CACHE_KEY_VERSION = "v1"


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


def make_cache_key(namespace: str, **fields: Any) -> str:
    """统一缓存 key 生成：固定前缀 + 版本 + 命名空间 + 核心参数排序后的哈希。

    对字段按 key 排序后序列化再做 sha256，保证参数顺序不同也能命中同一缓存，
    同时避免长文本直接出现在 key 中。
    """
    payload = json.dumps(fields, ensure_ascii=False, sort_keys=True, default=str)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"resume:{CACHE_KEY_VERSION}:{namespace}:{digest}"


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


def cache_get_json(key: str, metadata: Optional[dict] = None) -> Optional[Any]:
    raw = cache_get(key)
    if raw is None:
        logger.info("cache MISS key=%s meta=%s", key, metadata or {})
        return None
    try:
        data = json.loads(raw)
    except Exception:
        logger.warning("cache HIT but unreadable key=%s meta=%s", key, metadata or {})
        return None
    logger.info("cache HIT  key=%s meta=%s", key, metadata or {})
    return data


def cache_set_json(key: str, value: Any, ttl: int | None = None) -> None:
    cache_set(key, json.dumps(value, ensure_ascii=False), ttl=ttl)
