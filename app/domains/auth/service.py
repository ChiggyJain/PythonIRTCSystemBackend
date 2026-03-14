
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
        # create access token
        # -------------------------

        access_token = create_access_token(
            user_id=user_id,
        )

        # -------------------------
        # optional: log access token
        # -------------------------

        access_expire = now_ist() + timedelta(
            minutes=settings.JWT_ACCESS_EXPIRE_MINUTES
        )

        await self.repo.create_token(
            user_id=user_id,
            token=access_token,
            token_type="access",
            expires_at=access_expire,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # -------------------------
        # prepare refresh expiry
        # -------------------------

        refresh_expire = now_ist() + timedelta(
            days=settings.JWT_REFRESH_EXPIRE_DAYS
        )

        # -------------------------
        # create DB row first
        # -------------------------

        token_row = await self.repo.create_token(
            user_id=user_id,
            token="temp",
            token_type="refresh",
            expires_at=refresh_expire,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # -------------------------
        # create refresh token with id
        # -------------------------

        refresh_token = create_refresh_token(
            user_id=user_id,
            token_id=token_row.id,
        )

        # -------------------------
        # update DB token value
        # -------------------------

        token_row.token = refresh_token
        token_row.updated_at = now_ist()

        await self.repo.db.commit()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
        }


    # =========================
    # revoke token
    # =========================

    async def revoke(
        self,
        token_id: int,
    ):

        await self.repo.revoke_token(
            token_id
        )


    # =========================
    # get refresh token
    # =========================

    async def get_refresh(
        self,
        token_id: int,
    ):

        return await self.repo.get_by_id(
            token_id
        )