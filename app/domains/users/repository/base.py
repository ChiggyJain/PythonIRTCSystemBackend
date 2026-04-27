
"""
Users Repository Base Interface
Defines repository contract.
All implementations must follow this.
"""

from abc import (
    ABC, abstractmethod
)
from typing import Any
from app.domains.users.models.users_model import Users


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
        profile: str
    ) -> Users:
        pass

    @abstractmethod
    async def get_by_id(
        self,
        user_id: int,
    ) -> Users | None:
        pass

    @abstractmethod
    async def get_profile_snapshot_by_id(
        self,
        user_id: int,
    ) -> dict[str, Any] | None:
        """
        Lightweight profile-only projection (no full ORM object).
        Example return:
        {
            "id": 101,
            "first_name": "Chirag",
            "last_name": "Jain",
            "email": "abc@example.com",
            "is_email_verified": "Y",
            "email_verified_last_datetime": datetime(...),
            "mobile": "9876543210",
            "gender": "Male",
        }
        """
        pass
