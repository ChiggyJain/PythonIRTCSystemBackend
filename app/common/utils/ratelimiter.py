
from app.common.utils.logger import app_logger
from app.infrastructure.redis.client import get_redis


class RateLimiter:
    
    def __init__(self):
        self.redis = get_redis()

    async def check_window_limit(
        self,
        key: str,
        limit: int,
        window: int,
    ) -> bool:
    
        try:

            # Atomic increment
            value = await self.redis.incr(key)
            # Set TTL only when key created first time
            if value == 1:
                await self.redis.expire(key, window)
            # Check limit
            if value > limit:
                return False
            return True

        except Exception as e:

            # Log error but allow request
            app_logger.error(
                f"ratelimit error | key={key} | {e}"
            )

            # Fail-open: if Redis limiter fails, allow request.
            # (Do not block valid traffic because of limiter infra issue.)
            return True


# Singleton-style instance
rate_limiter = RateLimiter()