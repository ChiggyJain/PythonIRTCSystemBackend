
"""
Auth Token Repository Base (ABC)
Enterprise abstraction
"""

from abc import (
    ABC, abstractmethod
)
from typing import Optional
from app.domains.auth.usertokens_model import UserTokens


class TokenRepositoryBase(ABC):

    @abstractmethod
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
        pass

    @abstractmethod
    async def get_by_token(
        self,
        token_hash: str,
    ) -> Optional[UserTokens]:
        pass

    @abstractmethod
    async def get_by_id(
        self,
        token_id: int,
    ) -> Optional[UserTokens]:
        pass

    @abstractmethod
    async def revoke_token(
        self,
        token_id: int,
    ) -> None:
        pass

    @abstractmethod
    async def revoke_token_by_user(
        self,
        user_id: int,
    ) -> None:
        pass

    @abstractmethod
    async def commit(self) -> None:
        pass

    @abstractmethod
    async def rollback(self) -> None:
        pass