
from typing import (
    Any, List, Optional
)
from fastapi.responses import JSONResponse


def standardize_response(
    status_code: int = 404,
    messages: List[str] = None,
    data: Optional[Any] = None,
) -> JSONResponse:
       
    if messages is None:
       messages = [f"Unkown messages"]
    content = {
        "status_code": status_code,
        "messages": messages,
        "data": data,
    }
    return JSONResponse(
        status_code=status_code,
        content=content,
    )

