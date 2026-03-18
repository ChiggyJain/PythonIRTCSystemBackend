
"""
Email Verification OTP Service
Flow:
1) request -> create OTP_CHALLENGES + OUTBOX_EVENTS + SECURITY_EVENT_LOG
2) confirm -> verify OTP and mark USERS email verified
"""

from datetime import timedelta
import base64
import hashlib
import hmac
import secrets
from cryptography.fernet import Fernet
from app.common.utils.datetime import now_ist
from app.common.utils.logger import app_logger
from app.core.exceptions import BaseAppException
from app.core.settings import get_settings
from app.common.cache.config import CACHE_KEY_USER_PROFILE
from app.common.cache.redis_cache import build_cache_key, cache_delete
from app.domains.security.repository.base import SecurityRepositoryBase


settings = get_settings()


class EmailVerificationOtpService:

    OTP_PURPOSE_EMAIL_VERIFICATION = "EMAIL_VERIFICATION"
    OTP_STATUS_REQUESTED = "REQUESTED"
    OTP_STATUS_VERIFIED = "VERIFIED"
    OTP_STATUS_EXPIRED = "EXPIRED"
    OTP_STATUS_BLOCKED = "BLOCKED"
    OTP_TTL_SECONDS = 300
    OTP_MAX_ATTEMPTS = 5
    OTP_REQUEST_COOLDOWN_SECONDS = 60
    OTP_CIPHER_KEY_VERSION = "v1"
    OUTBOX_STATUS_PENDING = "PENDING"
    OUTBOX_EVENT_TYPE = "EMAILVERIFICATION_OTP_DISPATCH_REQUESTED_V1"


    def __init__(
        self,
        repo: SecurityRepositoryBase,
    ):
        self.repo = repo
        self._otp_hash_secret = f"{settings.JWT_SECRET_KEY}:otp-hash:v1"
        self._fernet = self._build_fernet(
            secret=f"{settings.JWT_SECRET_KEY}:otp-cipher:v1"
        )


    async def request_email_verification_otp(
        self,
        *,
        user_id: int,
        channel: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        correlation_id: str | None = None,
        request_id: str | None = None,
    ) -> dict:

        channel = (channel or "").strip().upper()
        if channel != "EMAIL":
            raise BaseAppException(status_code=400, messages=["channel must be EMAIL"])

        user = await self.repo.get_active_user(user_id)
        if not user:
            raise BaseAppException(status_code=404, messages=["User not found"])

        if user.is_email_verified == "Y":
            raise BaseAppException(status_code=400, messages=["Email already verified"])

        destination_raw = user.email
        destination_masked = self._mask_email(user.email)

        now = now_ist()

        # Cooldown + one-active policy
        active_otp_challenge = await self.repo.get_latest_active_otp_challenge(
            user_id=user_id,
            purpose=self.OTP_PURPOSE_EMAIL_VERIFICATION,
            channel="EMAIL",
            now_time=now,
        )
        if active_otp_challenge:
            elapsed_seconds = int((now - active_otp_challenge.created_at).total_seconds())
            if elapsed_seconds < self.OTP_REQUEST_COOLDOWN_SECONDS:
                retry_after_seconds = self.OTP_REQUEST_COOLDOWN_SECONDS - elapsed_seconds
                raise BaseAppException(
                    status_code=429,
                    messages=[f"OTP already requested. Please retry after {retry_after_seconds} seconds"],
                    data={
                        "retry_after_seconds": retry_after_seconds,
                        "challenge_id": active_otp_challenge.challenge_id,
                    },
                )

            expires_in_sec = max(0, int((active_otp_challenge.expires_at - now).total_seconds()))
            return {
                "challenge_id": active_otp_challenge.challenge_id,
                "expires_in_sec": expires_in_sec,
                "destination_masked": active_otp_challenge.destination_masked,
                "dispatch_status": "already_active",
            }

        otp = self._generate_otp()
        otp_hash = self._hash_otp(otp)
        otp_ciphertext = self._encrypt_otp(otp)

        challenge_id = self._build_challenge_id(user_id)
        expires_at = now + timedelta(seconds=self.OTP_TTL_SECONDS)

        try:
            
            await self.repo.add_otp_challenge(
                challenge_id=challenge_id,
                user_id=user_id,
                purpose=self.OTP_PURPOSE_EMAIL_VERIFICATION,
                channel="EMAIL",
                destination_masked=destination_masked,
                otp_hash=otp_hash,
                otp_ciphertext=otp_ciphertext,
                cipher_key_version=self.OTP_CIPHER_KEY_VERSION,
                expires_at=expires_at,
                max_attempts=self.OTP_MAX_ATTEMPTS,
                status=self.OTP_STATUS_REQUESTED,
            )

            await self.repo.add_outbox_event(
                aggregate_type="OTP_CHALLENGE",
                aggregate_id=challenge_id,
                event_type=self.OUTBOX_EVENT_TYPE,
                payload_json={
                    "challenge_id": challenge_id,
                    "user_id": user_id,
                    "purpose": self.OTP_PURPOSE_EMAIL_VERIFICATION,
                    "channel": "EMAIL",
                    "destination": destination_raw,
                },
                status=self.OUTBOX_STATUS_PENDING,
            )

            await self.repo.add_security_event(
                user_id=user_id,
                event_name="email_verification_otp_requested",
                event_category="EMAIL_VERIFICATION",
                channel="EMAIL",
                provider=None,
                status="accepted",
                reason_code=None,
                correlation_id=correlation_id,
                request_id=request_id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata_json={
                    "challenge_id": challenge_id,
                    "purpose": self.OTP_PURPOSE_EMAIL_VERIFICATION,
                    "expires_in_sec": self.OTP_TTL_SECONDS,
                },
            )

            await self.repo.commit()

        except Exception:
            await self.repo.rollback()
            raise

        return {
            "challenge_id": challenge_id,
            "expires_in_sec": self.OTP_TTL_SECONDS,
            "destination_masked": destination_masked,
            "dispatch_status": "accepted",
        }


    async def confirm_email_verification_otp(
        self,
        *,
        user_id: int,
        challenge_id: str,
        otp: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        correlation_id: str | None = None,
        request_id: str | None = None,
    ) -> dict:

        try:
            challenge = await self.repo.get_otp_challenge_for_update(
                challenge_id=challenge_id,
                user_id=user_id,
                purpose=self.OTP_PURPOSE_EMAIL_VERIFICATION,
            )
            if not challenge:
                raise BaseAppException(status_code=400, messages=["Invalid OTP challenge"])

            now = now_ist()

            if challenge.status == self.OTP_STATUS_VERIFIED:
                raise BaseAppException(status_code=400, messages=["OTP already used"])

            # boundary-safe expiry check
            if challenge.expires_at <= now:
                challenge.status = self.OTP_STATUS_EXPIRED
                challenge.last_error_code = "OTP_EXPIRED"
                challenge.updated_at = now
                await self.repo.add_security_event(
                    user_id=user_id,
                    event_name="email_verification_otp_failed",
                    event_category="EMAIL_VERIFICATION",
                    channel="EMAIL",
                    provider=None,
                    status="expired",
                    reason_code="OTP_EXPIRED",
                    correlation_id=correlation_id,
                    request_id=request_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    metadata_json={"challenge_id": challenge_id},
                )
                await self.repo.commit()
                raise BaseAppException(status_code=400, messages=["OTP expired"])

            if challenge.attempts_used >= challenge.max_attempts:
                challenge.status = self.OTP_STATUS_BLOCKED
                challenge.last_error_code = "OTP_ATTEMPTS_EXCEEDED"
                challenge.updated_at = now
                await self.repo.commit()
                raise BaseAppException(status_code=400, messages=["OTP attempts exceeded"])

            if not self._verify_otp(otp=otp, otp_hash=challenge.otp_hash):
                challenge.attempts_used += 1
                challenge.updated_at = now
                challenge.last_error_code = "OTP_INVALID"
                if challenge.attempts_used >= challenge.max_attempts:
                    challenge.status = self.OTP_STATUS_BLOCKED

                await self.repo.add_security_event(
                    user_id=user_id,
                    event_name="email_verification_otp_failed",
                    event_category="EMAIL_VERIFICATION",
                    channel="EMAIL",
                    provider=None,
                    status="rejected",
                    reason_code="OTP_INVALID",
                    correlation_id=correlation_id,
                    request_id=request_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    metadata_json={
                        "challenge_id": challenge_id,
                        "attempts_used": challenge.attempts_used,
                        "max_attempts": challenge.max_attempts,
                    },
                )
                await self.repo.commit()
                raise BaseAppException(status_code=400, messages=["Invalid OTP"])

            verified_at = now_ist()
            updated = await self.repo.mark_user_email_verified(
                user_id=user_id,
                verified_at=verified_at,
            )
            if not updated:
                await self.repo.rollback()
                raise BaseAppException(status_code=404, messages=["User not found"])

            challenge.attempts_used += 1
            challenge.status = self.OTP_STATUS_VERIFIED
            challenge.last_error_code = None
            challenge.updated_at = verified_at

            await self.repo.add_security_event(
                user_id=user_id,
                event_name="email_verification_otp_verified",
                event_category="EMAIL_VERIFICATION",
                channel="EMAIL",
                provider=None,
                status="verified",
                reason_code=None,
                correlation_id=correlation_id,
                request_id=request_id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata_json={"challenge_id": challenge_id},
            )

            await self.repo.add_security_event(
                user_id=user_id,
                event_name="email_verified",
                event_category="EMAIL_VERIFICATION",
                channel="EMAIL",
                provider=None,
                status="success",
                reason_code=None,
                correlation_id=correlation_id,
                request_id=request_id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata_json={"challenge_id": challenge_id},
            )

            # DB first
            await self.repo.commit()

        except BaseAppException:
            raise
        except Exception:
            await self.repo.rollback()
            raise

        # cache cleanup best-effort (post-commit)
        try:
            user_profile_cache_key = build_cache_key(CACHE_KEY_USER_PROFILE, user_id)
            await cache_delete(user_profile_cache_key)
        except Exception as exc:
            app_logger.warning(
                f"email_verification cache_delete failed | user_id={user_id} | error={str(exc)}"
            )

        return {
            "email_verified": True
        }


    def _generate_otp(self) -> str:
        return f"{secrets.randbelow(900000) + 100000}"

    def _build_challenge_id(self, user_id: int) -> str:
        ts = now_ist().strftime("%Y%m%d%H%M%S")
        rand = secrets.token_hex(3).upper()
        return f"EMAILVERIFY_{user_id}_{ts}_{rand}"

    def _hash_otp(self, otp: str) -> str:
        return hmac.new(
            self._otp_hash_secret.encode("utf-8"),
            otp.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _verify_otp(self, *, otp: str, otp_hash: str) -> bool:
        return hmac.compare_digest(self._hash_otp(otp), otp_hash)

    def _build_fernet(self, *, secret: str) -> Fernet:
        digest = hashlib.sha256(secret.encode("utf-8")).digest()
        key = base64.urlsafe_b64encode(digest)
        return Fernet(key)

    def _encrypt_otp(self, otp: str) -> str:
        return self._fernet.encrypt(otp.encode("utf-8")).decode("utf-8")

    def _mask_email(self, email: str) -> str:
        if "@" not in email:
            return "***"
        local, domain = email.split("@", 1)
        if not local:
            return f"***@{domain}"
        if len(local) == 1:
            return f"{local[0]}***@{domain}"
        return f"{local[0]}***{local[-1]}@{domain}"
