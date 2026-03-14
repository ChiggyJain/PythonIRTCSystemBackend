
"""
Auth dependencies
"""

from fastapi import (
    Depends, Header
)
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.session import get_db
from app.domains.auth.service import TokenService
from app.domains.auth.repository.sqlalchemy_repo import (
    TokenRepositorySQLAlchemy,
)
from app.core.exceptions import BaseAppException
from app.common.security.jwt import decode_token
from app.domains.auth.service import TokenService


# =========================
# token service
# =========================

def get_token_service(
    db: AsyncSession = Depends(get_db),
) -> TokenService:

    repo = TokenRepositorySQLAlchemy(db)
    return TokenService(repo)



# =========================
# get current user
# =========================

async def get_current_user(
    authorization: str | None = Header(
        default=None
    ),
    token_service: TokenService = Depends(
        get_token_service
    ),
):

    if not authorization:
        raise BaseAppException(
            messages=["Authorization header missing"],
            status_code=401,
        )

    if not authorization.startswith("Bearer "):
        raise BaseAppException(
            messages=["Invalid authorization header"],
            status_code=401,
        )

    token = authorization.split(" ")[1]
    payload = decode_token(token)

    if not payload:
        raise BaseAppException(
            messages=["Invalid token"],
            status_code=401,
        )

    if payload.get("type") != "access":
        raise BaseAppException(
            messages=["Invalid token type"],
            status_code=401,
        )

    user_id = payload.get("sub")

    """
    token_row = await token_service.repo.get_by_token(token)
    if not token_row:

        raise BaseAppException(
            messages=["Token not found"],
            status_code=401,
        )
    if token_row.revoked:
        raise BaseAppException(
            messages=["Token revoked"],
            status_code=401,
        )
    """        

    return int(user_id)