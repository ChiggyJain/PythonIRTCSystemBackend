
"""
SQLAlchemy Token Repository
"""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.auth.models import UserTokens
from app.domains.auth.repository.base import (
    TokenRepositoryBase,
)
from app.common.utils.datetime import now_ist


class TokenRepositorySQLAlchemy(
    TokenRepositoryBase
):

    def __init__(
        self,
        db: AsyncSession,
    ):
        self.db = db


    # -------------------------
    # create token
    # -------------------------

    async def create_token(
        self,
        *,
        user_id: int,
        token: str,
        token_type: str,
        expires_at,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> UserTokens:

        obj = UserTokens(
            user_id=user_id,
            token=token,
            token_type=token_type,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
            revoked=False,
            status="A",
            created_at=now_ist(),
            updated_at=now_ist(),
        )
        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj


    # -------------------------
    # get by token
    # -------------------------

    async def get_by_token(
        self,
        token: str,
    ) -> UserTokens | None:

        stmt = select(UserTokens).where(
            UserTokens.token == token,
            UserTokens.status == "A",
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()
    

    # -------------------------
    # get by id
    # -------------------------

    async def get_by_id(
        self,
        token_id: int,
    ) -> UserTokens | None:

        stmt = select(UserTokens).where(
            UserTokens.id == token_id,
            UserTokens.status == "A",
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()


    # -------------------------
    # revoke
    # -------------------------

    async def revoke_token(
        self,
        token_id: int,
    ) -> None:

        stmt = (
            update(UserTokens)
            .where(UserTokens.id == token_id)
            .values(
                revoked=True,
                updated_at=now_ist(),
                status="Z",
            )
        )
        await self.db.execute(stmt)
        await self.db.commit()