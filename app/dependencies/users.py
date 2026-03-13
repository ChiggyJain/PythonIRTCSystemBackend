"""
Users dependencies

Provides service instances.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import get_db

from app.domains.users.service import UsersService
from app.domains.users.repository.sqlalchemy_repo import (
    UsersSQLAlchemyRepository,
)


# =========================================================
# Users Service Dependency
# =========================================================


def get_users_service(
    db: AsyncSession = Depends(get_db),
) -> UsersService:
    """
    Dependency to provide UsersService
    """

    repo = UsersSQLAlchemyRepository(db)

    service = UsersService(repo)

    return service