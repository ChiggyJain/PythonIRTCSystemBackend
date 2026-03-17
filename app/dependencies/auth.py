
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
from app.common.cache.redis_cache import (
    cache_get
)


# =========================
# token service
# =========================

def get_token_service(
    db: AsyncSession = Depends(get_db),
) -> TokenService:

    repo = TokenRepositorySQLAlchemy(db)
    return TokenService(repo)



# ==========================================
# get current user id from access_token
# ==========================================

async def get_current_user_id_from_access_token(
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
    jti = payload.get("jti")
    user_id_from_access_token_cache = await cache_get(key=f"cache:auth:user:access:jti:{jti}")
    if user_id_from_access_token_cache ==  None:
        raise BaseAppException(
            messages=["Access-Token (User-ID) is not found in stored cache"],
            status_code=401,
        )
    if int(user_id) != int(user_id_from_access_token_cache):
        raise BaseAppException(
            messages=["Access-Token (User-ID) is not matched with stored cache"],
            status_code=401,
        )
       
    return int(user_id)



# ==================================================
# get current user details from access token
# ===================================================

async def get_current_user_details_from_access_token(
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
    jti = payload.get("jti")
    user_id_from_access_token_cache = await cache_get(key=f"cache:auth:user:access:jti:{jti}")
    if user_id_from_access_token_cache == None:
        raise BaseAppException(
            messages=["Invalid access token. Access token is not available into cache"],
            status_code=401,
        )
    if int(user_id) != int(user_id_from_access_token_cache):
        raise BaseAppException(
            messages=["Access-Token (User-ID) is not matched with stored cache"],
            status_code=401,
        )
       
    return payload



# ==========================================
# get current user id from refresh token
# ==========================================

async def get_current_user_id_from_refresh_token(
    refresh_token: str,
):

    # decode the refresh token
    payload = decode_token(refresh_token)

    if not payload:
        raise BaseAppException(
            messages=["Invalid refresh token"],
            status_code=401,
        )

    if payload.get("type") != "refresh":
        raise BaseAppException(
            messages=["Invalid refresh token type"],
            status_code=401,
        )

    user_id = payload.get("sub")

    return int(user_id)


# ===================================================
# get current user details from refresh token
# ===================================================

async def get_current_user_details_from_refresh_token(
    refresh_token: str,
):

    # decode the refresh token
    payload = decode_token(refresh_token)

    if not payload:
        raise BaseAppException(
            messages=["Invalid refresh token"],
            status_code=401,
        )

    if payload.get("type") != "refresh":
        raise BaseAppException(
            messages=["Invalid refresh token type"],
            status_code=401,
        )

    return payload



















