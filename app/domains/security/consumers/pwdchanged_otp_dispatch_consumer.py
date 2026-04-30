
import asyncio
import base64
import hashlib
from cryptography.fernet import Fernet
from app.infrastructure.database.session import AsyncSessionLocal
from app.common.utils.datetime import now_ist
from app.core.settings import get_settings
from app.infrastructure.otp.provider_factory import get_emailverification_email_otp_sender
from app.domains.security.providers.base import OtpSendResult
from app.domains.security.repository.base import SecurityRepositoryBase


settings = get_settings()


class PwdChangedOtpDispatchConsumerService:
    OTP_PURPOSE_PASSWORD_CHANGE = "PASSWORD_CHANGE"

    # Provider send tuning (kept local so no settings.py change needed right now)
    SEND_MAX_ATTEMPTS = 3
    SEND_RETRY_BASE_SECONDS = 0.2
    SEND_PROVIDER_TIMEOUT_SECONDS = 10.0

    def __init__(
        self,
        *,
        repo: SecurityRepositoryBase,
        email_sender: EmailOtpSenderBase,
        sms_sender: SmsOtpSenderBase,
    ):
        self.repo = repo
        self.email_sender = email_sender
        self.sms_sender = sms_sender
        self._fernet = self._build_fernet(
            secret=f"{settings.JWT_SECRET_KEY}:otp-cipher:v1"
        )

    async def process_payload(
        self,
        payload: dict,
    ) -> None:
        
        """
        Example payload:
        {
          "outbox_id": 101,
          "event_type": "PWDCHANGED_OTP_DISPATCH_REQUESTED_V1",
          "challenge_id": "PWDCHG_101_20260318_ABC123",
          "user_id": 101,
          "purpose": "PASSWORD_CHANGE",
          "channel": "EMAIL",
          "destination": "user@example.com",
          "correlation_id": "corr-123",
          "request_id": "req-456"
        }
        """

        user_id = self._safe_int(payload.get("user_id"), default=0)
        challenge_id = str(payload.get("challenge_id") or "").strip()
        destination = str(payload.get("destination") or "").strip()
        correlation_id = str(payload.get("correlation_id") or "") or None
        request_id = str(payload.get("request_id") or "") or None

        # Invalid payload -> skip safely (no crash / no endless retry loop)
        if user_id <= 0 or not challenge_id or not destination:
            return

        try:

            challenge = await self.repo.get_otp_challenge_by_challenge_id_for_update(
                challenge_id=challenge_id
            )
            if not challenge:
                await self.repo.add_security_event(
                    user_id=user_id,
                    event_name="otp_dispatch_failed",
                    event_category="OTP",
                    channel=None,
                    provider=None,
                    status="failed",
                    reason_code="CHALLENGE_NOT_FOUND",
                    correlation_id=correlation_id,
                    request_id=request_id,
                    ip_address=None,
                    user_agent=None,
                    metadata_json={"challenge_id": challenge_id},
                )
                await self.repo.commit()
                return

            # Ensure this consumer handles only password-change OTP
            if challenge.purpose != self.OTP_PURPOSE_PASSWORD_CHANGE:
                await self.repo.add_security_event(
                    user_id=challenge.user_id,
                    event_name="otp_dispatch_skipped",
                    event_category="OTP",
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
                await self.repo.commit()
                return

            # Terminal/idempotent statuses (duplicate Kafka deliveries should not resend OTP)
            if challenge.status in {"VERIFIED", "EXPIRED", "BLOCKED", "SENT", "DISPATCH_FAILED"}:
                await self.repo.add_security_event(
                    user_id=challenge.user_id,
                    event_name="otp_dispatch_skipped",
                    event_category="OTP",
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
                await self.repo.commit()
                return

            now = now_ist()

            # Do not send expired OTP even if event arrives late from Kafka
            if challenge.expires_at <= now:
                await self.repo.mark_otp_challenge_status(
                    challenge=challenge,
                    status="EXPIRED",
                    last_error_code="OTP_EXPIRED",
                    updated_at=now,
                )
                await self.repo.add_security_event(
                    user_id=challenge.user_id,
                    event_name="otp_dispatch_skipped",
                    event_category="OTP",
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
                await self.repo.commit()
                return

            otp = self._decrypt_otp(challenge.otp_ciphertext)

            result = await self._send_with_retry(
                channel=challenge.channel,
                destination=destination,
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
                    user_id=challenge.user_id,
                    event_name="otp_dispatched",
                    event_category="OTP",
                    channel=challenge.channel,
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
                await self.repo.mark_otp_challenge_status(
                    challenge=challenge,
                    status="DISPATCH_FAILED",
                    last_error_code=result.error_code or "DISPATCH_FAILED",
                    updated_at=now,
                )
                await self.repo.add_security_event(
                    user_id=challenge.user_id,
                    event_name="otp_dispatch_failed",
                    event_category="OTP",
                    channel=challenge.channel,
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

            await self.repo.commit()

        except Exception:
            await self.repo.rollback()
            raise


    async def _send_with_retry(
        self,
        *,
        channel: str,
        destination: str,
        otp: str,
        purpose: str,
        challenge_id: str,
    ) -> OtpSendResult:
        
        """
        Retries provider call with small backoff and per-attempt timeout.
        """

        last_result = OtpSendResult(
            accepted=False,
            provider="UNKNOWN",
            error_code="UNKNOWN",
            error_message="unknown",
        )

        for attempt in range(1, self.SEND_MAX_ATTEMPTS + 1):
            try:
                result = await asyncio.wait_for(
                    self._send_once(
                        channel=channel,
                        destination=destination,
                        otp=otp,
                        purpose=purpose,
                        challenge_id=challenge_id,
                    ),
                    timeout=self.SEND_PROVIDER_TIMEOUT_SECONDS,
                )

                if result.accepted:
                    return result

                last_result = result

            except asyncio.TimeoutError:
                last_result = OtpSendResult(
                    accepted=False,
                    provider="UNKNOWN",
                    error_code="PROVIDER_TIMEOUT",
                    error_message=f"provider timeout > {self.SEND_PROVIDER_TIMEOUT_SECONDS}s",
                )
            except Exception as exc:
                last_result = OtpSendResult(
                    accepted=False,
                    provider="UNKNOWN",
                    error_code="PROVIDER_EXCEPTION",
                    error_message=str(exc),
                )

            if attempt < self.SEND_MAX_ATTEMPTS:
                await asyncio.sleep(self.SEND_RETRY_BASE_SECONDS * attempt)

        return last_result


    async def _send_once(
        self,
        *,
        channel: str,
        destination: str,
        otp: str,
        purpose: str,
        challenge_id: str,
    ) -> OtpSendResult:
        if channel == "EMAIL":
            return await self.email_sender.send_otp(
                to_email=destination,
                otp=otp,
                purpose=purpose,
                challenge_id=challenge_id,
            )

        if channel == "MOBILE":
            return await self.sms_sender.send_otp(
                to_mobile=destination,
                otp=otp,
                purpose=purpose,
                challenge_id=challenge_id,
            )

        return OtpSendResult(
            accepted=False,
            provider="UNKNOWN",
            error_code="INVALID_CHANNEL",
            error_message=f"unsupported channel={channel}",
        )


    def _build_fernet(
        self,
        *,
        secret: str,
    ) -> Fernet:
        digest = hashlib.sha256(secret.encode("utf-8")).digest()
        key = base64.urlsafe_b64encode(digest)
        return Fernet(key)

    def _decrypt_otp(
        self,
        ciphertext: str,
    ) -> str:
        decrypted = self._fernet.decrypt(ciphertext.encode("utf-8"))
        return decrypted.decode("utf-8")


    @staticmethod
    def _safe_int(
        value: object,
        default: int = 0,
    ) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
