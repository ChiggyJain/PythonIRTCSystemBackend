"""
Repository providers
This module provides repository instances.
Purpose:
---------
- select repo implementation
- keep service DB-agnostic
- support multiple DB in future
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.session import get_db
from app.domains.users.repository.base import (
    UsersRepositoryBase,
)
from app.domains.users.repository.sqlalchemy_repo import (
    UsersSQLAlchemyRepository,
)


# =========================================================
# Users repository provider
# =========================================================

def get_users_repository(
    db: AsyncSession = Depends(get_db),
) -> UsersRepositoryBase:
    """
    Returns repository implementation.
    Current:
        SQLAlchemy
    Future:
        MongoDB
        Postgres
        Memory repo
        Mock repo
    """

    repo: UsersRepositoryBase = (
        UsersSQLAlchemyRepository(db)
    )

    return repo