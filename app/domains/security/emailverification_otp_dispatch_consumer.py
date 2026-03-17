
"""
Kafka consumer handler for email-verification OTP dispatch.
"""

import asyncio
import base64
import hashlib
from cryptography.fernet import Fernet
from app.common.utils.datetime import now_ist
from app.core.settings import get_settings
from app.domains.security.providers.base import (
    EmailOtpSenderBase,
    OtpSendResult,
)
from app.domains.security.repository.base import SecurityRepositoryBase


settings = get_settings()


class EmailVerificationOtpDispatchConsumerService:

    def __init__(
        self,
        *,
        repo: SecurityRepositoryBase,
        email_sender: EmailOtpSenderBase,
    ):
        self.repo = repo
        self.email_sender = email_sender
        self._fernet = self._build_fernet(secret=f"{settings.JWT_SECRET_KEY}:otp-cipher:v1")

    async def process_payload(self, payload: dict) -> None:
        user_id = int(payload.get("user_id") or 0)
        challenge_id = str(payload.get("challenge_id") or "")
        destination = str(payload.get("destination") or "")

        if not challenge_id or not destination or user_id <= 0:
            return

        try:
            challenge = await self.repo.get_otp_challenge_by_challenge_id_for_update(
                challenge_id=challenge_id
            )
            if not challenge:
                await self.repo.rollback()
                return

            if challenge.status in {"VERIFIED", "EXPIRED", "BLOCKED"}:
                await self.repo.commit()
                return

            otp = self._decrypt_otp(challenge.otp_ciphertext)

            result = await self._send_with_retry(
                to_email=destination,
                otp=otp,
                purpose=challenge.purpose,
                challenge_id=challenge.challenge_id,
            )

            now = now_ist()
            if result.accepted:
                await self.repo.mark_otp_challenge_status(
                    challenge=challenge,
                    status="SENT",
                    last_error_code=None,
                    updated_at=now,
                )
                await self.repo.add_security_event(
                    user_id=user_id,
                    event_name="email_verification_otp_dispatched",
                    event_category="PROFILE_VERIFICATION",
                    channel="EMAIL",
                    provider=result.provider,
                    status="sent",
                    reason_code=None,
                    correlation_id=None,
                    request_id=None,
                    ip_address=None,
                    user_agent=None,
                    metadata_json={"challenge_id": challenge.challenge_id},
                )
            else:
                await self.repo.mark_otp_challenge_status(
                    challenge=challenge,
                    status="DISPATCH_FAILED",
                    last_error_code=result.error_code or "DISPATCH_FAILED",
                    updated_at=now,
                )
                await self.repo.add_security_event(
                    user_id=user_id,
                    event_name="email_verification_otp_failed",
                    event_category="PROFILE_VERIFICATION",
                    channel="EMAIL",
                    provider=result.provider,
                    status="failed",
                    reason_code=result.error_code or "DISPATCH_FAILED",
                    correlation_id=None,
                    request_id=None,
                    ip_address=None,
                    user_agent=None,
                    metadata_json={
                        "challenge_id": challenge.challenge_id,
                        "error": (result.error_message or "")[:500],
                    },
                )

            await self.repo.commit()

        except Exception:
            await self.repo.rollback()
            raise

    async def _send_with_retry(
        self,
        *,
        to_email: str,
        otp: str,
        purpose: str,
        challenge_id: str,
    ) -> OtpSendResult:
        last_result = OtpSendResult(
            accepted=False,
            provider="UNKNOWN",
            error_code="UNKNOWN",
            error_message="unknown",
        )

        for attempt in range(1, 4):
            try:
                result = await self.email_sender.send_otp(
                    to_email=to_email,
                    otp=otp,
                    purpose=purpose,
                    challenge_id=challenge_id,
                )
                if result.accepted:
                    return result
                last_result = result
            except Exception as exc:
                last_result = OtpSendResult(
                    accepted=False,
                    provider="UNKNOWN",
                    error_code="PROVIDER_EXCEPTION",
                    error_message=str(exc),
                )

            if attempt < 3:
                await asyncio.sleep(0.2 * attempt)

        return last_result

    def _build_fernet(self, *, secret: str) -> Fernet:
        digest = hashlib.sha256(secret.encode("utf-8")).digest()
        return Fernet(base64.urlsafe_b64encode(digest))

    def _decrypt_otp(self, ciphertext: str) -> str:
        return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
