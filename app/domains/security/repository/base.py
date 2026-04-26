
"""
Security Repository Base Interface
"""

from abc import (
    ABC, abstractmethod
)
from datetime import datetime
from typing import Any
from app.domains.users.users_model import Users
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
        metadata_json: str | None = None,
    ) -> OtpChallenges:
        pass
    
    @abstractmethod
    async def get_latest_active_otp_challenge(
        self,
        *,
        user_id: int,
        purpose: str,
        channel: str,
        now_time: datetime,
    ) -> OtpChallenges | None:
        """
        Return latest active (non-expired) OTP challenge for user+purpose+channel.
        Active statuses considered: REQUESTED, SENT.
        """
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
    async def get_otp_challenge_by_challenge_id_for_update(
        self,
        *,
        challenge_id: str,
    ) -> OtpChallenges | None:
        pass

    @abstractmethod
    async def mark_otp_challenge_status(
        self,
        *,
        challenge: OtpChallenges,
        status: str,
        last_error_code: str | None,
        updated_at: datetime,
    ) -> None:
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
    async def fetch_pending_outbox_events(
        self,
        *,
        event_type: str,
        limit: int,
        now_time: datetime,
    ) -> list[OutboxEvents]:
        pass

    @abstractmethod
    async def mark_outbox_published(
        self,
        *,
        event: OutboxEvents,
        published_at: datetime,
    ) -> None:
        pass

    @abstractmethod
    async def mark_outbox_retry(
        self,
        *,
        event: OutboxEvents,
        next_retry_at: datetime,
        last_error: str,
        updated_at: datetime,
    ) -> None:
        pass

    @abstractmethod
    async def mark_outbox_failed(
        self,
        *,
        event: OutboxEvents,
        last_error: str,
        updated_at: datetime,
    ) -> None:
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

    @abstractmethod
    async def mark_user_email_verified(
        self,
        *,
        user_id: int,
        verified_at: datetime,
    ) -> bool:
        """
        Mark user's current email as verified.
        Example:
            await repo.mark_user_email_verified(
                user_id=101,
                verified_at=now_ist(),
            )
        """
        pass


    @abstractmethod
    async def get_active_user_by_email(
        self,
        email: str,
    ) -> Users | None:
        pass


    @abstractmethod
    async def mark_user_email_changed_verified(
        self,
        *,
        user_id: int,
        new_email: str,
        verified_at: datetime,
    ) -> bool:
        pass

