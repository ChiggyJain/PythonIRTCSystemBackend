
"""
SQLAlchemy Token Repository
"""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from app.domains.auth.models.usertokens_models import UserTokens
from app.domains.auth.repository.base import (
    TokenRepositoryBase,
)
from app.common.utils.datetime import now_ist


class TokenRepositorySQLAlchemy(
    TokenRepositoryBase
):

    def __init__(self, db_session: AsyncSession):
        self._db_session = db_session


    # -------------------------
    # create token
    # -------------------------

    async def create_token(
        self,
        *,
        user_id: int,
        token_hash: str,
        token_type: str,
        expires_at,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> UserTokens:

        obj = UserTokens(
            user_id=user_id,
            token_hash=token_hash,
            token_type=token_type,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
            revoked=False,
            status="A",
            created_at=now_ist(),
            updated_at=now_ist(),
        )
        self._db_session.add(obj)
        # Important: flush gets auto-increment ID without committing transaction.
        await self._db_session.flush()
        return obj


    # -------------------------
    # get by token
    # -------------------------

    async def get_by_token(
        self,
        token_hash: str,
    ) -> UserTokens | None:

        stmt = select(UserTokens).where(
            UserTokens.token_hash == token_hash,
            UserTokens.status == "A",
        )
        res = await self._db_session.execute(stmt)
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
        res = await self._db_session.execute(stmt)
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
        await self._db_session.execute(stmt)
        # await self._db_session.commit()

    
    # -------------------------
    # revoke by user
    # -------------------------

    async def revoke_token_by_user(
        self,
        user_id: int,
    ) -> None:

        stmt = (
            update(UserTokens)
            .where(
                (UserTokens.user_id == user_id) 
                    &
                (UserTokens.revoked == 0) 
                    &
                (UserTokens.status == 'A')
            )
            .values(
                revoked=True,
                updated_at=now_ist(),
                status="Z",
            )
        )
        await self._db_session.execute(stmt)


    async def commit(self) -> None:
        await self._db_session.commit()

    async def rollback(self) -> None:
        await self._db_session.rollback()
