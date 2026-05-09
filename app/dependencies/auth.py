
from fastapi import (
    Depends
)
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.session import get_db
from app.domains.auth.services.auth_services import AuthService
from app.domains.auth.services.token_services import TokenService


def get_auth_service(
    db_session: AsyncSession = Depends(get_db),
) -> AuthService:
    return AuthService(db_session)


def get_token_service(
    db_session: AsyncSession = Depends(get_db),
) -> TokenService:
    return TokenService(db_session)



















