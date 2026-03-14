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

from typing import Callable
from fastapi.routing import APIRoute
from fastapi import Request, Response
from app.common.utils.logger import app_logger
from app.common.utils.ratelimiter import rate_limiter
from app.common.utils.datetime import now_ist
from app.common.utils.execution_context import get_worker_name


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
        given_api_name = feature_config.get("name", "unknown")
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

            worker = get_worker_name()
            extracted_api_name = request.url.path.split("/")[-1]
            ip = request.client.host if request.client else "unknown"
            method = request.method    
            path = request.url.path
            start_time = now_ist()
            status_code = 200
            error = None

            # -------------------------
            # Rate limit
            # -------------------------

            if rate_limit_config:

                limit = rate_limit_config.get("limit")
                window = rate_limit_config.get("window")
                key = f"ratelimit:{given_api_name}:ip:{ip}"
                allowed = await rate_limiter.check_window_limit(
                    key=key,
                    limit=limit,
                    window=window,
                )
                if not allowed:
                    end_time = now_ist()
                    duration = int((end_time - start_time).total_seconds() * 1000)
                    status_code = 429
                    error = 'Request limit exceeded'
                    log_msg = (
                        f"{worker} | {given_api_name} | {ip} | {method} | {path} | "
                        f"{start_time} | {end_time} | {duration} | {error} | {status_code}"
                    )
                    app_logger.error(log_msg)
                    from app.core.response import error_response
                    return error_response(
                        messages=["Too many requests"],
                        status_code=429,
                    )

            try:

                response: Response = await original_handler(request)
                status_code = response.status_code
                error = None
                return response

            except Exception as e:

                status_code = 500
                error = str(e)
                raise

            finally:

                end_time = now_ist()
                duration = int((end_time - start_time).total_seconds() * 1000)
                if error:

                    log_msg = (
                        f"{worker} | {given_api_name} | {ip} | {method} | {path} | "
                        f"{start_time} | {end_time} | {duration} | {error} | {status_code}"
                    )
                    app_logger.error(log_msg)

                else:

                    if logging_enabled:
                        log_msg = (
                            f"{worker} | {given_api_name} | {ip} | {method} | {path} | "
                            f"{start_time} | {end_time} | {duration} | {status_code}"
                        )
                        app_logger.info(log_msg)


        return custom_handler