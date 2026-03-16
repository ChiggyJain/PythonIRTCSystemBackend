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
        extra = ":".join(str(p) for p in parts)
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



# =========================
# build set key
# =========================

def build_cache_set_key(
    namespace: str,
    *parts: Any,
) -> str:
    """
    Build a cache set key.
    Example:
        key = build_cache_set_key("auth:user_access_index", 101)
        # key -> "auth:user_access_index:101"
    """
    key = namespace
    if parts:
        key = f"{namespace}:{':'.join(str(p) for p in parts)}"
    return key


# =========================
# add set members
# =========================

async def cache_set_add(
    key: str,
    *members: str,
    ttl: int | None = None,
) -> int:
    
    """
    Add one or more members into cache set.
    Returns:
        Number of NEW members added (existing members are ignored).
    Example:
        added = await cache_set_add(
            "auth:user_access_index:101",
            "jti_abc",
            "jti_xyz",
            ttl=900,
        )
    """

    if not members:
        return 0
    
    redis = get_redis()
    added = int(await redis.sadd(key, *members))

    # Optional TTL for auto cleanup.
    if ttl is not None:
        await redis.expire(key, ttl)

    return added


# =========================
# get all set members
# =========================

async def cache_set_members(
    key: str,
) -> set[str]:
    """
    Fetch all members from cache set.
    Example:
        jtis = await cache_set_members("auth:user_access_index:101")
        # {"jti_abc", "jti_xyz"}
    """
    redis = get_redis()
    values = await redis.smembers(key)
    if not values:
        return set()
    return {str(v) for v in values}


# =========================
# remove set members
# =========================

async def cache_set_remove(
    key: str,
    *members: str,
) -> int:
    
    """
    Remove one or more members from cache set.
    Returns:
        Number of members actually removed.
    Example:
        removed = await cache_set_remove(
            "auth:user_access_index:101",
            "jti_abc",
            "jti_xyz",
        )
    """

    if not members:
        return 0

    redis = get_redis()
    return int(await redis.srem(key, *members))



# =========================
# set size
# =========================

async def cache_set_size(
    key: str,
) -> int:
    
    """
    Count members in cache set.
    Example:
        total = await cache_set_size("auth:user_access_index:101")
    """

    redis = get_redis()
    return int(await redis.scard(key))



# =========================
# check member exists
# =========================

async def cache_set_contains(
    key: str,
    member: str,
) -> bool:
    """
    Check if member exists in cache set.
    Example:
        exists = await cache_set_contains(
            "auth:user_access_index:101",
            "jti_abc",
        )
    """
    redis = get_redis()
    return bool(await redis.sismember(key, member))



# =========================
# delete entire set key
# =========================

async def cache_set_delete(
    key: str,
) -> int:
    
    """
    Delete entire cache set key.
    Returns:
        1 if key deleted, 0 if key not found.
    Example:
        await cache_set_delete("auth:user_access_index:101")
    """
    
    redis = get_redis()
    return int(await redis.delete(key))

