
"""
FastAPI Exception Handlers
Handles errors not caught by middleware.
Handles:
---------
- HTTPException
- ValidationError
- RequestValidationError
- Generic Exception
All responses converted to standard format.
"""

from fastapi import (
    FastAPI, Request
)
from fastapi.exceptions import RequestValidationError
from fastapi import HTTPException
from app.core.response import build_response


# =========================================================
# Register handlers
# =========================================================


def register_exception_handlers(app: FastAPI):
    """
    Register all exception handlers
    """

    # -------------------------
    # HTTPException
    # -------------------------

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request,
        exc: HTTPException,
    ):
        return build_response(
            status_code=exc.status_code,
            messages=[str(exc.detail)],
            data=None,
        )

    # -------------------------
    # Validation Error
    # -------------------------

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ):

        errors = []

        for err in exc.errors():
            msg = err.get("msg")
            # remove "Value error, "
            if msg.startswith("Value error,"):
                msg = msg.replace("Value error,", "").strip()
            errors.append(msg)

        return build_response(
            status_code=422,
            messages=errors,
            data=None,
        )

    # -------------------------
    # Unknown Exception
    # -------------------------

    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request,
        exc: Exception,
    ):
        return build_response(
            status_code=500,
            messages=["Internal Server Error"],
            data=None,
        )