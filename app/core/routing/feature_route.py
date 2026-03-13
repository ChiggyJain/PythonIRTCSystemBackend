"""
Feature APIRoute (Enterprise)

This route supports feature_control decorator.

Features supported:
-------------------
- logging
- rate limiting
- timing
- future auth / audit / metrics

Used only when route_class=FeatureAPIRoute
"""

import time
from typing import Callable

from fastapi.routing import APIRoute
from fastapi import Request, Response

from app.common.utils.logger import app_logger
from app.common.utils.ratelimiter import rate_limiter


class FeatureAPIRoute(APIRoute):
    """
    Route class that supports feature_control config
    """

    def get_route_handler(self) -> Callable:

        original_handler = super().get_route_handler()

        endpoint = self.endpoint

        feature_config = getattr(
            endpoint,
            "__feature_config__",
            {},
        )

        name = feature_config.get("name", "unknown")

        logging_enabled = feature_config.get(
            "logging",
            False,
        )

        rate_limit_config = feature_config.get(
            "rate_limit",
            None,
        )

        async def custom_handler(
            request: Request,
        ) -> Response:

            start_time = time.time()

            ip = request.client.host if request.client else "unknown"

            method = request.method

            path = request.url.path

            # -------------------------
            # Rate limit
            # -------------------------

            if rate_limit_config:

                limit = rate_limit_config.get("limit")
                window = rate_limit_config.get("window")

                key = f"ratelimit:{name}:ip:{ip}"

                allowed = await rate_limiter.check_window_limit(
                    key=key,
                    limit=limit,
                    window=window,
                )

                if not allowed:

                    app_logger.warning(
                        f"{name} | {ip} | rate limit exceeded"
                    )

                    from app.core.response import error_response

                    return error_response(
                        messages=["Too many requests"],
                        status_code=429,
                    )

            # -------------------------
            # Logging start
            # -------------------------

            if logging_enabled:

                app_logger.info(
                    f"{name} | {ip} | {method} | {path} | start"
                )

            try:

                response: Response = await original_handler(
                    request
                )

                duration = int(
                    (time.time() - start_time) * 1000
                )

                if logging_enabled:

                    app_logger.info(
                        f"{name} | {ip} | {method} | {path} | "
                        f"{response.status_code} | "
                        f"{duration}ms"
                    )

                return response

            except Exception as e:

                duration = int(
                    (time.time() - start_time) * 1000
                )

                app_logger.error(
                    f"{name} | {ip} | {method} | {path} | "
                    f"error | {duration}ms | {e}"
                )

                raise

        return custom_handler