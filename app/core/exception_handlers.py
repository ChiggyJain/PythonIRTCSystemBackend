
from fastapi import (
    FastAPI, Request
)
from fastapi.exceptions import RequestValidationError
from fastapi import HTTPException
from pydantic import ValidationError
from app.core.response import standardize_response


def register_exception_handlers(app: FastAPI):
    
    # HTTPException
    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request,
        exc: HTTPException,
    ):
        return standardize_response(
            status_code=exc.status_code,
            messages=[str(exc.detail)],
            data=None,
        )


    # FastAPI Request Validation
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

        return standardize_response(
            status_code=422,
            messages=errors,
            data=None,
        )


    # Pydantic Validation Error
    @app.exception_handler(ValidationError)
    async def pydantic_validation_exception_handler(
        request: Request,
        exc: ValidationError,
    ):

        errors = []
        for err in exc.errors():
            msg = err.get("msg")
            if msg.startswith("Value error,"):
                msg = msg.replace("Value error,", "").strip()
            errors.append(msg)

        return standardize_response(
            status_code=422,
            messages=errors,
            data=None,
        )
    

    # Unknown Exception
    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request,
        exc: Exception,
    ):
        return standardize_response(
            status_code=500,
            messages=["Internal Server Error"],
            data=None,
        )