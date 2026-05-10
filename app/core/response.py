
from typing import (
    Any, List, Optional
)
from fastapi.responses import JSONResponse


def standardize_response(
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

