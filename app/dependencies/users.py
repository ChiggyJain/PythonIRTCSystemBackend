"""
Users dependencies
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.session import get_db
from app.domains.users.services.services import UsersService


def get_users_service(
    db_session: AsyncSession = Depends(get_db),
) -> UsersService:
    return UsersService(db_session)