
"""
Auth dependencies
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.session import get_db
from app.domains.auth.service import TokenService
from app.domains.auth.repository.sqlalchemy_repo import (
    TokenRepositorySQLAlchemy,
)


# =========================
# token service
# =========================

def get_token_service(
    db: AsyncSession = Depends(get_db),
) -> TokenService:

    repo = TokenRepositorySQLAlchemy(db)

    return TokenService(repo)