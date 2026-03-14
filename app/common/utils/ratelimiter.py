
"""
Redis Rate Limiter (Enterprise)

Features:
---------
- async safe
- multi-worker safe
- generic key based
- window based limit
- Redis atomic increment
- future-proof design

Supported future use cases:
---------------------------
- IP limit
- user limit
- token limit
- global limit
- route limit
- role limit
"""

from app.common.utils.logger import app_logger
from app.infrastructure.redis.client import get_redis


class RateLimiter:
    """
    Generic Redis Rate Limiter
    This limiter works using:
        key + limit + window
    Example keys:
        ratelimit:v1.users.signup:ip:1.1.1.1
        ratelimit:v1.users.signup:user:45
        ratelimit:global
    """

    def __init__(self):
        # Redis client (async)
        self.redis = get_redis()

    async def check_window_limit(
        self,
        key: str,
        limit: int,
        window: int,
    ) -> bool:
        """
        Check window limit using Redis.
        Parameters
        ----------
        key : str
            Unique key for limiter
        limit : int
            Max allowed requests
        window : int
            Time window in seconds
        Returns
        -------
        bool
            True  -> allowed
            False -> blocked
        """

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

            # Fail open (production rule)
            return True


# Singleton-style instance
rate_limiter = RateLimiter()