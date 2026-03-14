
"""
Redis client
Provides async Redis instance.
"""

from redis.asyncio import Redis
from app.core.settings import get_settings

_settings = get_settings()

redis_client: Redis | None = None


# =========================================================
# Get Redis instance
# =========================================================

def get_redis() -> Redis:
    """
    Returns singleton Redis client
    """

    global redis_client
    if redis_client is None:
        redis_client = Redis(
            host=_settings.REDIS_HOST,
            port=_settings.REDIS_PORT,
            db=_settings.REDIS_DB,
            decode_responses=True,
        )
    return redis_client