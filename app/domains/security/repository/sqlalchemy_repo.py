"""
Security SQLAlchemy Repository
"""

from datetime import datetime
from typing import Any
from sqlalchemy import select, update, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.users.models.users_models import Users
from app.domains.auth.models.usertokens_models import UserTokens
from app.domains.security.models.models import (
    OtpChallenges,
    SecurityEventLog,
)
from app.domains.security.repository.base import SecurityRepositoryBase
from app.common.utils.datetime import now_ist


class SecuritySQLAlchemyRepository(SecurityRepositoryBase):

    def __init__(
        self,
        db_session: AsyncSession,
    ):
        self._db_session = db_session


    async def get_active_user(
        self,
        user_id: int,
    ) -> Users | None:

        stmt = select(Users).where(
            Users.id == user_id,
            Users.status == "A",
        )
        res = await self._db_session.execute(stmt)
        return res.scalar_one_or_none()


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

        row = OtpChallenges(
            challenge_id=challenge_id,
            user_id=user_id,
            purpose=purpose,
            channel=channel,
            destination_masked=destination_masked,
            otp_hash=otp_hash,
            otp_ciphertext=otp_ciphertext,
            cipher_key_version=cipher_key_version,
            expires_at=expires_at,
            max_attempts=max_attempts,
            attempts_used=0,
            status=status,
            last_error_code=None,
            metadata_json=metadata_json,
            created_at=now_ist(),
            updated_at=now_ist(),
        )
        self._db_session.add(row)
        await self._db_session.flush()
        return row


    async def get_latest_active_otp_challenge(
        self,
        *,
        user_id: int,
        purpose: str,
        channel: str,
        now_time: datetime,
    ) -> OtpChallenges | None:

        stmt = (
            select(OtpChallenges)
            .where(
                OtpChallenges.user_id == user_id,
                OtpChallenges.purpose == purpose,
                OtpChallenges.channel == channel,
                OtpChallenges.status.in_(["REQUESTED", "SENT"]),
                OtpChallenges.expires_at > now_time,
            )
            .order_by(OtpChallenges.created_at.desc())
            .limit(1)
        )
        res = await self._db_session.execute(stmt)
        return res.scalar_one_or_none()


    async def get_otp_challenge_for_update(
        self,
        *,
        challenge_id: str,
        user_id: int,
        purpose: str,
    ) -> OtpChallenges | None:

        stmt = (
            select(OtpChallenges)
            .where(
                OtpChallenges.challenge_id == challenge_id,
                OtpChallenges.user_id == user_id,
                OtpChallenges.purpose == purpose,
            )
            .with_for_update()
        )
        res = await self._db_session.execute(stmt)
        return res.scalar_one_or_none()


    async def get_otp_challenge_by_challenge_id_for_update(
        self,
        *,
        challenge_id: str,
    ) -> OtpChallenges | None:

        stmt = (
            select(OtpChallenges)
            .where(OtpChallenges.challenge_id == challenge_id)
            .with_for_update()
        )
        res = await self._db_session.execute(stmt)
        return res.scalar_one_or_none()


    async def mark_otp_challenge_status(
        self,
        *,
        challenge: OtpChallenges,
        status: str,
        last_error_code: str | None,
        updated_at: datetime,
    ) -> None:

        challenge.status = status
        challenge.last_error_code = last_error_code
        challenge.updated_at = updated_at
        await self._db_session.flush()


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

        row = SecurityEventLog(
            user_id=user_id,
            event_name=event_name,
            event_category=event_category,
            channel=channel,
            provider=provider,
            status=status,
            reason_code=reason_code,
            correlation_id=correlation_id,
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata_json=metadata_json,
            created_at=now_ist(),
        )
        self._db_session.add(row)
        await self._db_session.flush()
        return row


    async def update_user_password(
        self,
        *,
        user_id: int,
        password_hash: str,
        changed_at: datetime,
    ) -> bool:

        stmt = (
            update(Users)
            .where(
                Users.id == user_id,
                Users.status == "A",
            )
            .values(
                password=password_hash,
                updated_at=changed_at,
            )
        )
        res = await self._db_session.execute(stmt)
        return bool(res.rowcount and res.rowcount > 0)


    async def revoke_active_tokens_for_user(
        self,
        *,
        user_id: int,
        changed_at: datetime,
    ) -> int:

        stmt = (
            update(UserTokens)
            .where(
                UserTokens.user_id == user_id,
                UserTokens.status == "A",
                UserTokens.revoked.is_(False),
            )
            .values(
                revoked=True,
                updated_at=changed_at,
                status="Z",
            )
        )
        res = await self._db_session.execute(stmt)
        return int(res.rowcount or 0)


    async def mark_user_email_verified(
        self,
        *,
        user_id: int,
        verified_at: datetime,
    ) -> bool:

        stmt = (
            update(Users)
            .where(
                Users.id == user_id,
                Users.status == "A",
            )
            .values(
                is_email_verified="Y",
                email_verified_last_datetime=verified_at,
                updated_at=verified_at,
            )
        )
        res = await self._db_session.execute(stmt)
        return bool(res.rowcount and res.rowcount > 0)
    

    async def get_active_user_by_email(
        self,
        email: str,
    ) -> Users | None:

        stmt = select(Users).where(
            Users.email == email,
            Users.status == "A",
        )
        res = await self._db_session.execute(stmt)
        return res.scalar_one_or_none()
    

    async def mark_user_email_changed_verified(
        self,
        *,
        user_id: int,
        new_email: str,
        verified_at: datetime,
    ) -> bool:

        stmt = (
            update(Users)
            .where(
                Users.id == user_id,
                Users.status == "A",
            )
            .values(
                email=new_email,
                is_email_verified="Y",
                email_verified_last_datetime=verified_at,
                updated_at=verified_at,
            )
        )
        res = await self._db_session.execute(stmt)
        return bool(res.rowcount and res.rowcount > 0)

    
    
    async def commit(self) -> None:
        await self._db_session.commit()

    async def rollback(self) -> None:
        await self._db_session.rollback()
