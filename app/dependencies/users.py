"""
Users dependencies
"""

from fastapi import Depends
from app.domains.users.service import UsersService
from app.domains.users.repository.base import (
    UsersRepositoryBase,
)
from app.dependencies.repositories import (
    get_users_repository,
)


def get_users_service(
    repo: UsersRepositoryBase = Depends(
        get_users_repository
    ),
) -> UsersService:
    """
    Provide UsersService
    """

    return UsersService(repo)