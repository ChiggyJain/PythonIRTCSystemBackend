
"""
Password Change OTP Service
Step 2 scope:
- OTP challenge creation
- Outbox row creation (Kafka publish will be separate worker step)
- OTP verification for password change
- Password update + token revoke
"""

from datetime import timedelta
import base64
import hashlib
import hmac
import secrets
from cryptography.fernet import Fernet
from app.common.utils.datetime import now_ist
from app.common.utils.password import hash_password
from app.core.exceptions import BaseAppException
from app.core.settings import get_settings
from app.domains.security.repository.base import SecurityRepositoryBase


settings = get_settings()


class PasswordChangeOtpService:

    OTP_PURPOSE_PASSWORD_CHANGE = "PASSWORD_CHANGE"
    OTP_STATUS_REQUESTED = "REQUESTED"
    OTP_STATUS_SENT = "SENT"
    OTP_STATUS_VERIFIED = "VERIFIED"
    OTP_STATUS_EXPIRED = "EXPIRED"
    OTP_STATUS_BLOCKED = "BLOCKED"
    OUTBOX_STATUS_PENDING = "PENDING"
    OUTBOX_EVENT_OTP_DISPATCH_REQUESTED = "OTP_DISPATCH_REQUESTED_V1"
    OTP_TTL_SECONDS = 300
    OTP_MAX_ATTEMPTS = 5
    OTP_CIPHER_KEY_VERSION = "v1"

    def __init__(
        self,
        repo: SecurityRepositoryBase,
    ):
        self.repo = repo
        self._otp_hash_secret = f"{settings.JWT_SECRET_KEY}:otp-hash:v1"
        self._fernet = self._build_fernet(
            secret=f"{settings.JWT_SECRET_KEY}:otp-cipher:v1"
        )

    # =========================
    # public: request OTP
    # =========================

    async def request_password_change_otp(
        self,
        *,
        user_id: int,
        channel: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        correlation_id: str | None = None,
        request_id: str | None = None,
    ) -> dict:

        channel = self._normalize_channel(channel)
        user = await self.repo.get_active_user(user_id)
        if not user:
            raise BaseAppException(
                status_code=404,
                messages=["User not found"],
            )

        destination_raw, destination_masked = self._get_destination(
            channel=channel,
            email=user.email,
            mobile=user.mobile,
        )

        otp = self._generate_otp()
        otp_hash = self._hash_otp(otp)
        otp_ciphertext = self._encrypt_otp(otp)

        challenge_id = self._build_challenge_id(user_id)
        now = now_ist()
        expires_at = now + timedelta(seconds=self.OTP_TTL_SECONDS)

        try:
            await self.repo.add_otp_challenge(
                challenge_id=challenge_id,
                user_id=user_id,
                purpose=self.OTP_PURPOSE_PASSWORD_CHANGE,
                channel=channel,
                destination_masked=destination_masked,
                otp_hash=otp_hash,
                otp_ciphertext=otp_ciphertext,
                cipher_key_version=self.OTP_CIPHER_KEY_VERSION,
                expires_at=expires_at,
                max_attempts=self.OTP_MAX_ATTEMPTS,
                status=self.OTP_STATUS_REQUESTED,
            )

            # Outbox event only (Kafka publish is separate step)
            await self.repo.add_outbox_event(
                aggregate_type="OTP_CHALLENGE",
                aggregate_id=challenge_id,
                event_type=self.OUTBOX_EVENT_OTP_DISPATCH_REQUESTED,
                payload_json={
                    "challenge_id": challenge_id,
                    "user_id": user_id,
                    "purpose": self.OTP_PURPOSE_PASSWORD_CHANGE,
                    "channel": channel,
                    "destination": destination_raw,
                },
                status=self.OUTBOX_STATUS_PENDING,
            )

            await self.repo.add_security_event(
                user_id=user_id,
                event_name="otp_requested",
                event_category="OTP",
                channel=channel,
                provider=None,
                status="accepted",
                reason_code=None,
                correlation_id=correlation_id,
                request_id=request_id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata_json={
                    "challenge_id": challenge_id,
                    "purpose": self.OTP_PURPOSE_PASSWORD_CHANGE,
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

    # =========================
    # public: confirm OTP + change password
    # =========================

    async def confirm_password_change(
        self,
        *,
        user_id: int,
        challenge_id: str,
        otp: str,
        new_password: str,
        confirm_password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        correlation_id: str | None = None,
        request_id: str | None = None,
    ) -> dict:

        if new_password != confirm_password:
            raise BaseAppException(
                status_code=400,
                messages=["password and confirm password must match"],
            )

        try:
            challenge = await self.repo.get_otp_challenge_for_update(
                challenge_id=challenge_id,
                user_id=user_id,
                purpose=self.OTP_PURPOSE_PASSWORD_CHANGE,
            )
            if not challenge:
                raise BaseAppException(
                    status_code=400,
                    messages=["Invalid OTP challenge"],
                )

            now = now_ist()

            if challenge.status == self.OTP_STATUS_VERIFIED:
                raise BaseAppException(
                    status_code=400,
                    messages=["OTP already used"],
                )

            if challenge.expires_at < now:
                challenge.status = self.OTP_STATUS_EXPIRED
                challenge.last_error_code = "OTP_EXPIRED"
                challenge.updated_at = now

                await self.repo.add_security_event(
                    user_id=user_id,
                    event_name="otp_verification_failed",
                    event_category="OTP",
                    channel=challenge.channel,
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

                raise BaseAppException(
                    status_code=400,
                    messages=["OTP expired"],
                )

            if challenge.attempts_used >= challenge.max_attempts:
                challenge.status = self.OTP_STATUS_BLOCKED
                challenge.last_error_code = "OTP_ATTEMPTS_EXCEEDED"
                challenge.updated_at = now
                await self.repo.commit()

                raise BaseAppException(
                    status_code=400,
                    messages=["OTP attempts exceeded"],
                )

            if not self._verify_otp(otp=otp, otp_hash=challenge.otp_hash):
                challenge.attempts_used += 1
                challenge.updated_at = now
                challenge.last_error_code = "OTP_INVALID"

                if challenge.attempts_used >= challenge.max_attempts:
                    challenge.status = self.OTP_STATUS_BLOCKED

                await self.repo.add_security_event(
                    user_id=user_id,
                    event_name="otp_verification_failed",
                    event_category="OTP",
                    channel=challenge.channel,
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

                raise BaseAppException(
                    status_code=400,
                    messages=["Invalid OTP"],
                )

            changed_at = now_ist()
            password_hash = hash_password(new_password)

            updated = await self.repo.update_user_password(
                user_id=user_id,
                password_hash=password_hash,
                changed_at=changed_at,
            )
            if not updated:
                await self.repo.rollback()
                raise BaseAppException(
                    status_code=404,
                    messages=["User not found"],
                )

            revoked_count = await self.repo.revoke_active_tokens_for_user(
                user_id=user_id,
                changed_at=changed_at,
            )

            challenge.attempts_used += 1
            challenge.status = self.OTP_STATUS_VERIFIED
            challenge.last_error_code = None
            challenge.updated_at = changed_at

            await self.repo.add_security_event(
                user_id=user_id,
                event_name="otp_verified",
                event_category="OTP",
                channel=challenge.channel,
                provider=None,
                status="verified",
                reason_code=None,
                correlation_id=correlation_id,
                request_id=request_id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata_json={
                    "challenge_id": challenge_id,
                    "attempts_used": challenge.attempts_used,
                },
            )

            await self.repo.add_security_event(
                user_id=user_id,
                event_name="password_changed",
                event_category="ACCOUNT_SECURITY",
                channel=challenge.channel,
                provider=None,
                status="success",
                reason_code=None,
                correlation_id=correlation_id,
                request_id=request_id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata_json={
                    "challenge_id": challenge_id,
                    "sessions_revoked": revoked_count,
                },
            )

            await self.repo.commit()

        except BaseAppException:
            raise
        except Exception:
            await self.repo.rollback()
            raise

        return {
            "message": "Password changed successfully",
            "sessions_revoked": revoked_count,
        }

    # =========================
    # internal helpers
    # =========================

    def _normalize_channel(
        self,
        channel: str,
    ) -> str:

        value = (channel or "").strip().upper()
        if value not in {"EMAIL", "MOBILE"}:
            raise BaseAppException(
                status_code=400,
                messages=["channel must be EMAIL or MOBILE"],
            )
        return value

    def _get_destination(
        self,
        *,
        channel: str,
        email: str,
        mobile: str,
    ) -> tuple[str, str]:

        if channel == "EMAIL":
            return email, self._mask_email(email)

        if channel == "MOBILE":
            return mobile, self._mask_mobile(mobile)

        raise BaseAppException(
            status_code=400,
            messages=["Unsupported channel"],
        )

    def _mask_email(
        self,
        email: str,
    ) -> str:

        if "@" not in email:
            return "***"
        local, domain = email.split("@", 1)
        if not local:
            return f"***@{domain}"
        if len(local) == 1:
            masked_local = f"{local[0]}***"
        else:
            masked_local = f"{local[0]}***{local[-1]}"
        return f"{masked_local}@{domain}"

    def _mask_mobile(
        self,
        mobile: str,
    ) -> str:

        digits = "".join(ch for ch in mobile if ch.isdigit())
        if len(digits) < 4:
            return "******"
        return f"{digits[:2]}******{digits[-2:]}"

    def _generate_otp(self) -> str:
        return f"{secrets.randbelow(900000) + 100000}"

    def _build_challenge_id(
        self,
        user_id: int,
    ) -> str:

        ts = now_ist().strftime("%Y%m%d%H%M%S")
        rand = secrets.token_hex(3).upper()
        return f"PWDCHG_{user_id}_{ts}_{rand}"

    def _hash_otp(
        self,
        otp: str,
    ) -> str:

        return hmac.new(
            self._otp_hash_secret.encode("utf-8"),
            otp.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _verify_otp(
        self,
        *,
        otp: str,
        otp_hash: str,
    ) -> bool:

        candidate = self._hash_otp(otp)
        return hmac.compare_digest(candidate, otp_hash)

    def _build_fernet(
        self,
        *,
        secret: str,
    ) -> Fernet:

        digest = hashlib.sha256(secret.encode("utf-8")).digest()
        key = base64.urlsafe_b64encode(digest)
        return Fernet(key)

    def _encrypt_otp(
        self,
        otp: str,
    ) -> str:

        encrypted = self._fernet.encrypt(otp.encode("utf-8"))
        return encrypted.decode("utf-8")
