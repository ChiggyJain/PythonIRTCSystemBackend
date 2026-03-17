
"""
Auth Token Service

Handles JWT + DB tokens
"""

from datetime import timedelta

from app.common.security.jwt import (
    create_access_token,
    create_refresh_token,
)
from app.common.utils.datetime import now_ist
from app.core.settings import get_settings
from app.domains.auth.repository.base import (
    TokenRepositoryBase,
)
from app.common.cache.redis_cache import (
    build_cache_key,
    cache_set,
    build_cache_set_key,
    cache_set_add
)


settings = get_settings()


class TokenService:

    def __init__(
        self,
        repo: TokenRepositoryBase,
    ):
        self.repo = repo


    # =========================
    # create tokens (login)
    # =========================

    async def create_tokens(
        self,
        *,
        user_id: int,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ):


        # -------------------------
        # prepare access expiry
        # -------------------------

        access_expire = now_ist() + timedelta(
            minutes=settings.JWT_ACCESS_EXPIRE_MINUTES
        )
        access_expire_seconds = int(
            (access_expire - now_ist()).total_seconds()
        )
        
        # ------------------------------------------------------------
        # create DB row first for access-token to get generated row_id
        # ------------------------------------------------------------

        access_token_row = await self.repo.create_token(
            user_id=user_id,
            token="temp",
            token_type="access",
            expires_at=access_expire,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # ---------------------------------------------
        # prepare refresh expiry
        # ---------------------------------------------

        refresh_expire = now_ist() + timedelta(
            days=settings.JWT_REFRESH_EXPIRE_DAYS
        )

        # -------------------------------------------------------------
        # create DB row first for refresh token to get generated row id
        # -------------------------------------------------------------

        refresh_token_row = await self.repo.create_token(
            user_id=user_id,
            token="temp",
            token_type="refresh",
            expires_at=refresh_expire,
            ip_address=ip_address,
            user_agent=user_agent,
        )


        # ----------------------------
        # create access token with id
        # ----------------------------
        access_token = create_access_token(
            user_id=user_id,
            token_id=access_token_row.id,
            against_token_type="refresh",
            against_token_id=refresh_token_row.id
        )

        # -----------------------------
        # update DB access token value
        # -----------------------------

        access_token_row.token = access_token
        access_token_row.updated_at = now_ist()

        # -----------------------------
        # create refresh token with id
        # ------------------------------

        refresh_token = create_refresh_token(
            user_id=user_id,
            token_id=refresh_token_row.id,
            against_token_type="access",
            against_token_id=access_token_row.id
        )

        # -----------------------------
        # update DB refresh token value
        # -----------------------------

        refresh_token_row.token = refresh_token
        refresh_token_row.updated_at = now_ist()

        await self.repo.db.commit()

        # storing access-token-row-id into redis for respective user
        # key-value with expire seconds
        cacheKey = build_cache_key(f"auth:user:access:jti:{access_token_row.id}")
        await cache_set(key=cacheKey, value=user_id, ttl=access_expire_seconds)

        # storing all access-token-row-id into redis for respective user
        # set format
        cacheKey = build_cache_set_key(f"auth:user:access:index:{user_id}")
        await cache_set_add(cacheKey, str(access_token_row.id))

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
        }


    # =========================
    # revoke token
    # =========================

    async def revoke(
        self,
        token_id: int|str,
    ):

        await self.repo.revoke_token(token_id)


    
    # =========================
    # get access token
    # =========================

    async def get_access(
        self,
        token_id: int|str,
    ):

        return await self.repo.get_by_id(token_id)
    
    
    # =========================
    # get refresh token
    # =========================

    async def get_refresh(
        self,
        token_id: int|str,
    ):

        return await self.repo.get_by_id(token_id)