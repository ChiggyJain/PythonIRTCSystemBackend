
"""
Security Repository Base Interface
"""

from abc import (
    ABC, abstractmethod
)
from datetime import datetime
from typing import Any
from app.domains.users.models import Users
from app.domains.security.models import (
    OtpChallenges,
    OutboxEvents,
    SecurityEventLog,
)


class SecurityRepositoryBase(ABC):

    @abstractmethod
    async def get_active_user(
        self,
        user_id: int,
    ) -> Users | None:
        pass

    @abstractmethod
    async def add_otp_challenge(
        self,
        *,
        challenge_id: str,
        user_id: int,
        purpose: str,
        channel: str,
        destination_masked: str,
        otp_hash: str,
        otp_ciphertext: str,
        cipher_key_version: str,
        expires_at: datetime,
        max_attempts: int,
        status: str,
    ) -> OtpChallenges:
        pass

    @abstractmethod
    async def get_otp_challenge_for_update(
        self,
        *,
        challenge_id: str,
        user_id: int,
        purpose: str,
    ) -> OtpChallenges | None:
        pass

    @abstractmethod
    async def add_outbox_event(
        self,
        *,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload_json: dict[str, Any],
        status: str,
    ) -> OutboxEvents:
        pass

    @abstractmethod
    async def add_security_event(
        self,
        *,
        user_id: int,
        event_name: str,
        event_category: str,
        channel: str | None,
        provider: str | None,
        status: str,
        reason_code: str | None,
        correlation_id: str | None,
        request_id: str | None,
        ip_address: str | None,
        user_agent: str | None,
        metadata_json: dict[str, Any] | None,
    ) -> SecurityEventLog:
        pass

    @abstractmethod
    async def update_user_password(
        self,
        *,
        user_id: int,
        password_hash: str,
        changed_at: datetime,
    ) -> bool:
        pass

    @abstractmethod
    async def revoke_active_tokens_for_user(
        self,
        *,
        user_id: int,
        changed_at: datetime,
    ) -> int:
        pass

    @abstractmethod
    async def commit(self) -> None:
        pass

    @abstractmethod
    async def rollback(self) -> None:
        pass
