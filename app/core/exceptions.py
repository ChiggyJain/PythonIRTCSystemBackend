
from typing import (
    List, Optional, Any
)

class BaseAppException(Exception):
    def __init__(
        self,
        status_code: int,
        messages: List[str],
        data: Optional[Any] = None,
    ):
        self.status_code = status_code
        self.messages = messages
        self.data = data


