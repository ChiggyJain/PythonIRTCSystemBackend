
"""
Redis Cache Utility
Reusable cache helper
"""

import json
from typing import (
    Any, Optional
)
from app.infrastructure.redis.client import get_redis


# =========================
# build key
# =========================

def build_cache_key(
    name: str,
    *parts: Any,
) -> str:

    key = f"cache:{name}"
    if parts:
        extra = ":".join(
            str(p) for p in parts
        )
        key = f"{key}:{extra}"
    return key


# =========================
# get
# =========================

async def cache_get(
    key: str,
) -> Optional[Any]:

    redis = get_redis()
    value = await redis.get(key)
    if not value:
        return None
    try:
        return json.loads(value)
    except Exception:
        return None


# =========================
# set
# =========================

async def cache_set(
    key: str,
    value: Any,
    ttl: int = 300,
):

    redis = get_redis()
    data = json.dumps(value)
    await redis.set(
        key,
        data,
        ex=ttl,
    )


# =========================
# delete
# =========================

async def cache_delete(
    key: str,
):

    redis = get_redis()
    await redis.delete(key)