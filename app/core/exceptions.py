"""
Global Exception System

All custom exceptions must inherit from BaseAppException.

These exceptions will be converted to standard response format.

Design goals:
-------------
- global usage
- reusable
- safe for async
- safe for multi worker
- safe for middleware
"""

from typing import List, Optional


# =========================================================
# Base Exception
# =========================================================


class BaseAppException(Exception):
    """
    Base exception for application

    All custom exceptions must inherit this.
    """

    def __init__(
        self,
        status_code: int,
        messages: List[str],
        data: Optional[object] = None,
    ):
        self.status_code = status_code
        self.messages = messages
        self.data = data


# =========================================================
# Bad Request
# =========================================================


class BadRequestException(BaseAppException):
    """
    400 error
    """

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


# =========================================================
# Not Found
# =========================================================


class NotFoundException(BaseAppException):
    """
    404 error
    """

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


# =========================================================
# Unauthorized
# =========================================================


class UnauthorizedException(BaseAppException):
    """
    401 error
    """

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


# =========================================================
# Forbidden
# =========================================================


class ForbiddenException(BaseAppException):
    """
    403 error
    """

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


# =========================================================
# Conflict
# =========================================================


class ConflictException(BaseAppException):
    """
    409 error
    """

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


# =========================================================
# Internal Server Error
# =========================================================


class InternalServerException(BaseAppException):
    """
    500 error
    """

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