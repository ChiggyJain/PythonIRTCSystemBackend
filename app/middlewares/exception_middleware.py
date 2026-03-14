
"""
Exception Middleware
This middleware catches all exceptions
and converts them to standard response format.
Handles:
---------
- BaseAppException
- Runtime errors
- Unknown errors
- DB errors
- Async errors
- FastAPI errors not handled
Must be registered in main.py
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.response import build_response
from app.core.exceptions import BaseAppException


class ExceptionMiddleware(BaseHTTPMiddleware):
    """
    Global exception middleware
    """

    async def dispatch(self, request: Request, call_next):

        try:
            response = await call_next(request)
            return response

        # =========================
        # Custom App Exception
        # =========================

        except BaseAppException as exc:

            return build_response(
                status_code=exc.status_code,
                messages=exc.messages,
                data=exc.data,
            )

        # =========================
        # Unknown Exception
        # =========================

        except Exception as exc:

            return build_response(
                status_code=500,
                messages=["Internal Server Error"],
                data=None,
            )