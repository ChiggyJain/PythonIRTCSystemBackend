
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
    data: Any = None,
    messages: Optional[List[str]] = None,
    status_code: int = 200,
) -> JSONResponse:
    
    if messages is None:
        messages = ["Success"]

    return build_response(
        status_code=status_code,
        messages=messages,
        data=data,
    )


def error_response(
    messages: List[str],
    status_code: int = 400,
    data: Any = None,
) -> JSONResponse:
    
    return build_response(
        status_code=status_code,
        messages=messages,
        data=data,
    )



def exception_response(
    message: str = "Internal Server Error",
) -> JSONResponse:
    
    return build_response(
        status_code=500,
        messages=[message],
        data=None,
    )