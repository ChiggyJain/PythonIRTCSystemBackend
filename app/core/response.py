
"""
Standard API Response System
All APIs must return this format:
{
    "status_code": int,
    "messages": [str],
    "data": any
}
This module provides helper functions to create
standard responses.
Design goals:
-------------
- global usage
- reusable
- async safe
- multi-worker safe
- production safe
- FastAPI safe
"""


from typing import (
    Any, List, Optional
)
from fastapi.responses import JSONResponse


# =========================================================
# Base Response Builder
# =========================================================


def build_response(
    status_code: int,
    messages: List[str],
    data: Optional[Any] = None,
) -> JSONResponse:
    """
    Build standard JSON response
    Parameters
    ----------
    status_code : int
    messages : list[str]
    data : any
    Returns
    -------
    JSONResponse
    """

    content = {
        "status_code": status_code,
        "messages": messages,
        "data": data,
    }

    return JSONResponse(
        status_code=status_code,
        content=content,
    )


# =========================================================
# Success Response
# =========================================================


def success_response(
    data: Any = None,
    messages: Optional[List[str]] = None,
    status_code: int = 200,
) -> JSONResponse:
    """
    Success response
    """

    if messages is None:
        messages = ["Success"]

    return build_response(
        status_code=status_code,
        messages=messages,
        data=data,
    )


# =========================================================
# Error Response
# =========================================================


def error_response(
    messages: List[str],
    status_code: int = 400,
    data: Any = None,
) -> JSONResponse:
    """
    Error response
    """

    return build_response(
        status_code=status_code,
        messages=messages,
        data=data,
    )


# =========================================================
# Exception Response
# =========================================================


def exception_response(
    message: str = "Internal Server Error",
) -> JSONResponse:
    """
    System exception response
    """

    return build_response(
        status_code=500,
        messages=[message],
        data=None,
    )