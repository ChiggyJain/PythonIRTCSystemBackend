
from typing import (
    List, Optional
)

class BaseAppException(Exception):
    def __init__(
        self,
        status_code: int,
        messages: List[str],
        data: Optional[object] = None,
    ):
        self.status_code = status_code
        self.messages = messages
        self.data = data


class BadRequestException(BaseAppException):
    def __init__(
        self,
        messages: List[str] = ["Bad Request"],
        data: object = None,
    ):
        super().__init__(
            status_code=400,
            messages=messages,
            data=data,
        )


class NotFoundException(BaseAppException):
    def __init__(
        self,
        messages: List[str] = ["Not Found"],
        data: object = None,
    ):
        super().__init__(
            status_code=404,
            messages=messages,
            data=data,
        )


class UnauthorizedException(BaseAppException):
    def __init__(
        self,
        messages: List[str] = ["Unauthorized"],
        data: object = None,
    ):
        super().__init__(
            status_code=401,
            messages=messages,
            data=data,
        )


class ForbiddenException(BaseAppException):
    def __init__(
        self,
        messages: List[str] = ["Forbidden"],
        data: object = None,
    ):
        super().__init__(
            status_code=403,
            messages=messages,
            data=data,
        )

class ConflictException(BaseAppException):
    def __init__(
        self,
        messages: List[str] = ["Conflict"],
        data: object = None,
    ):
        super().__init__(
            status_code=409,
            messages=messages,
            data=data,
        )


class InternalServerException(BaseAppException):
    def __init__(
        self,
        messages: List[str] = ["Internal Server Error"],
        data: object = None,
    ):
        super().__init__(
            status_code=500,
            messages=messages,
            data=data,
        )