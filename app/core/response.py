
from typing import (
    Any, List, Optional
)
from fastapi.responses import JSONResponse


def build_response(
    status_code: int,
    messages: List[str],
    data: Optional[Any] = None,
) -> JSONResponse:

    content = {
        "status_code": status_code,
        "messages": messages,
        "data": data,
    }
    return JSONResponse(
        status_code=status_code,
        content=content,
    )


def success_response(
    status_code: int = 200,
    messages: Optional[List[str]] = None,
    data: Any = None,
) -> JSONResponse:
    
    if messages is None:
        messages = ["Success"]

    return build_response(
        status_code=status_code,
        messages=messages,
        data=data,
    )


def error_response(
    status_code: int = 400,
    messages: Optional[List[str]] = None,
    data: Any = None,
) -> JSONResponse:
    
    return build_response(
        status_code=status_code,
        messages=messages,
        data=data,
    )


def exception_response(
    status_code: int = 400,
    messages: Optional[List[str]] = None,
    data: Any = None,
) -> JSONResponse:
    
    return build_response(
        status_code=500,
        messages=messages,
        data=None,
    )