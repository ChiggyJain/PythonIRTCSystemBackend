

from redis.asyncio import Redis
from app.core.settings import get_settings

_settings = get_settings()

redis_client: Redis | None = None

def get_redis() -> Redis:
    global redis_client
    if redis_client is None:
        redis_client = Redis(
            host=_settings.REDIS_HOST,
            port=_settings.REDIS_PORT,
            db=_settings.REDIS_DB,
            decode_responses=True,
        )
    return redis_client