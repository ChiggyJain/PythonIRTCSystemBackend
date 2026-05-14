
import asyncio
import base64
import hashlib
import json
from cryptography.fernet import Fernet
from app.infrastructure.database.session import AsyncSessionLocal
from app.common.utils.datetime import now_ist
from app.core.settings import get_settings
from app.infrastructure.email.provider_factory import get_emailchanged_email_otp_sender
from app.infrastructure.email.base import (
    EmailSendResult,
)
from app.domains.security.repository.sqlalchemy_repo import SecuritySQLAlchemyRepository


settings = get_settings()



class EmailChangedOtpDispatchConsumerService:

    OTP_PURPOSE_EMAIL_CHANGE = "EMAIL_CHANGE"
    SEND_MAX_ATTEMPTS = 3
    SEND_RETRY_BASE_SECONDS = 0.2
    SEND_PROVIDER_TIMEOUT_SECONDS = 10.0

    def __init__(self):
        self.security_repo = None
        self.email_sender = get_emailchanged_email_otp_sender()
        self._otp_fernet = self._build_fernet(secret=f"{settings.JWT_SECRET_KEY}:otp-cipher:v1")
        self._meta_fernet = self._build_fernet(secret=f"{settings.JWT_SECRET_KEY}:otp-metadata-cipher:v1")


    async def process_payload(self, payload: dict) -> None:

        user_id = self._safe_int(payload.get("user_id"), default=0)
        challenge_id = str(payload.get("challenge_id") or "").strip()
        correlation_id = str(payload.get("correlation_id") or "") or None
        request_id = str(payload.get("request_id") or "") or None

        if not challenge_id or user_id <= 0:
            return

        async with AsyncSessionLocal() as db_session:

            try:
                
                self.security_repo = SecuritySQLAlchemyRepository(db_session)

                challenge = await self.security_repo.get_otp_challenge_by_challenge_id_for_update(challenge_id=challenge_id)
                if not challenge:
                    await self.security_repo.add_security_event(
                        user_id=user_id,
                        event_name="email_change_otp_failed",
                        event_category="EMAIL_CHANGE",
                        channel="EMAIL",
                        provider=None,
                        status="failed",
                        reason_code="CHALLENGE_NOT_FOUND",
                        correlation_id=correlation_id,
                        request_id=request_id,
                        ip_address=None,
                        user_agent=None,
                        metadata_json={"challenge_id": challenge_id},
                    )
                    await db_session.commit()
                    return

                if challenge.purpose != self.OTP_PURPOSE_EMAIL_CHANGE:
                    await self.security_repo.add_security_event(
                        user_id=challenge.user_id,
                        event_name="email_change_otp_dispatch_skipped",
                        event_category="EMAIL_CHANGE",
                        channel=challenge.channel,
                        provider=None,
                        status="ignored",
                        reason_code=f"PURPOSE_{challenge.purpose}",
                        correlation_id=correlation_id,
                        request_id=request_id,
                        ip_address=None,
                        user_agent=None,
                        metadata_json={"challenge_id": challenge.challenge_id},
                    )
                    await db_session.commit()
                    return

                if challenge.status in {"VERIFIED", "EXPIRED", "BLOCKED", "SENT", "DISPATCH_FAILED"}:
                    await self.security_repo.add_security_event(
                        user_id=challenge.user_id,
                        event_name="email_change_otp_dispatch_skipped",
                        event_category="EMAIL_CHANGE",
                        channel=challenge.channel,
                        provider=None,
                        status="ignored",
                        reason_code=f"STATUS_{challenge.status}",
                        correlation_id=correlation_id,
                        request_id=request_id,
                        ip_address=None,
                        user_agent=None,
                        metadata_json={"challenge_id": challenge.challenge_id},
                    )
                    await db_session.commit()
                    return

                now = now_ist()
                if challenge.expires_at <= now:
                    await self.security_repo.mark_otp_challenge_status(
                        challenge=challenge,
                        status="EXPIRED",
                        last_error_code="OTP_EXPIRED",
                        updated_at=now,
                    )
                    await self.security_repo.add_security_event(
                        user_id=challenge.user_id,
                        event_name="email_change_otp_dispatch_skipped",
                        event_category="EMAIL_CHANGE",
                        channel=challenge.channel,
                        provider=None,
                        status="expired",
                        reason_code="OTP_EXPIRED",
                        correlation_id=correlation_id,
                        request_id=request_id,
                        ip_address=None,
                        user_agent=None,
                        metadata_json={"challenge_id": challenge.challenge_id},
                    )
                    await db_session.commit()
                    return

                meta = self._decrypt_metadata_json(challenge.metadata_json)
                destination = (meta.get("new_email") or "").strip().lower()
                if not destination:
                    await self.security_repo.mark_otp_challenge_status(
                        challenge=challenge,
                        status="DISPATCH_FAILED",
                        last_error_code="MISSING_NEW_EMAIL",
                        updated_at=now_ist(),
                    )
                    await self.security_repo.add_security_event(
                        user_id=challenge.user_id,
                        event_name="email_change_otp_failed",
                        event_category="EMAIL_CHANGE",
                        channel="EMAIL",
                        provider=None,
                        status="failed",
                        reason_code="MISSING_NEW_EMAIL",
                        correlation_id=correlation_id,
                        request_id=request_id,
                        ip_address=None,
                        user_agent=None,
                        metadata_json={"challenge_id": challenge.challenge_id},
                    )
                    await db_session.commit()
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
                    await self.security_repo.mark_otp_challenge_status(
                        challenge=challenge,
                        status="SENT",
                        last_error_code=None,
                        updated_at=now,
                    )
                    await self.security_repo.add_security_event(
                        user_id=challenge.user_id,
                        event_name="email_change_otp_dispatched",
                        event_category="EMAIL_CHANGE",
                        channel="EMAIL",
                        provider=result.provider,
                        status="sent",
                        reason_code=None,
                        correlation_id=correlation_id,
                        request_id=request_id,
                        ip_address=None,
                        user_agent=None,
                        metadata_json={
                            "challenge_id": challenge.challenge_id,
                            "provider_message_id": result.provider_message_id,
                        },
                    )
                else:
                    await self.security_repo.mark_otp_challenge_status(
                        challenge=challenge,
                        status="DISPATCH_FAILED",
                        last_error_code=result.error_code or "DISPATCH_FAILED",
                        updated_at=now,
                    )
                    await self.security_repo.add_security_event(
                        user_id=challenge.user_id,
                        event_name="email_change_otp_failed",
                        event_category="EMAIL_CHANGE",
                        channel="EMAIL",
                        provider=result.provider,
                        status="failed",
                        reason_code=result.error_code or "DISPATCH_FAILED",
                        correlation_id=correlation_id,
                        request_id=request_id,
                        ip_address=None,
                        user_agent=None,
                        metadata_json={
                            "challenge_id": challenge.challenge_id,
                            "error": (result.error_message or "")[:500],
                        },
                    )

                await db_session.commit()

            except Exception:
                await db_session.rollback()
                raise


    async def _send_with_retry(self, *, to_email: str, otp: str, purpose: str, challenge_id: str) -> EmailSendResult:

        last_result = EmailSendResult(
            accepted=False,
            provider="UNKNOWN",
            provider_message_id ="UNKNOWN",
            error_code="UNKNOWN",
            error_message="unknown",
        )

        # Build email content
        subject = f"{settings.EMAILCHANGED_OTP_EMAIL_SUBJECT_PREFIX}"
        html_content = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                    <h2 style="color: #d9534f;">
                        Email Changing OTP Request Information
                    </h2>
                    <p>
                        Your OTP-Code: <strong>{otp}</strong> and OTP-ID: <strong>{challenge_id}</strong>. This OTP expires in 5 minutes.
                    </p>
                </body>
            </html>
        """

        for attempt in range(1, self.SEND_MAX_ATTEMPTS + 1):
            try:
                result = await self.email_sender.send_email(
                    to_email=to_email,
                    subject=subject,
                    html_content=html_content,
                )  
                if result.accepted:
                    return result
                last_result = result
            except asyncio.TimeoutError:
                last_result = EmailSendResult(
                    accepted=False,
                    provider="UNKNOWN",
                    provider_message_id ="UNKNOWN",
                    error_code="PROVIDER_TIMEOUT",
                    error_message=f"provider timeout > {self.SEND_PROVIDER_TIMEOUT_SECONDS}s",
                )
            except Exception as exc:
                last_result = EmailSendResult(
                    accepted=False,
                    provider="UNKNOWN",
                    provider_message_id ="UNKNOWN",
                    error_code="PROVIDER_EXCEPTION",
                    error_message=str(exc),
                )

            if attempt < self.SEND_MAX_ATTEMPTS:
                await asyncio.sleep(self.SEND_RETRY_BASE_SECONDS * attempt)

        return last_result



    def _build_fernet(self, *, secret: str) -> Fernet:
        digest = hashlib.sha256(secret.encode("utf-8")).digest()
        key = base64.urlsafe_b64encode(digest)
        return Fernet(key)

    def _decrypt_otp(self, ciphertext: str) -> str:
        return self._otp_fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")

    def _decrypt_metadata_json(self, ciphertext: str | None) -> dict:
        if not ciphertext:
            return {}
        try:
            raw = self._meta_fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
            obj = json.loads(raw)
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}

    @staticmethod
    def _safe_int(value: object, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
