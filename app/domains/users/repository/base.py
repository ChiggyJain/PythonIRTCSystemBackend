
"""
Users Repository Base Interface

Defines repository contract.

All implementations must follow this.
"""

from abc import ABC, abstractmethod

from app.domains.users.models import Users


class UsersRepositoryBase(ABC):
    """
    Abstract repository for USERS
    """

    @abstractmethod
    async def get_by_email(
        self,
        email: str,
    ) -> Users | None:
        pass

    @abstractmethod
    async def create_user(
        self,
        *,
        first_name: str,
        last_name: str,
        mobile: str,
        email: str,
        password: str,
        gender: str,
    ) -> Users:
        pass