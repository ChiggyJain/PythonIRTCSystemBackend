
from datetime import timedelta
import base64
import hashlib
import hmac
import secrets
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.utils.datetime import now_ist
from app.common.utils.logger import app_logger
from app.core.exceptions import BaseAppException
from app.core.response import (
    standardize_response, 
)
from app.core.settings import get_settings
from app.common.utils.ratelimiter import rate_limiter
from app.common.cache.redis_cache import cache_delete
from app.domains.security.repository.sqlalchemy_repo import SecuritySQLAlchemyRepository
from app.infrastructure.outbox.repository.sqlalchemy_repo import OutboxEventsSQLAlchemyRepository


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
    OUTBOX_EVENT_TYPE = "EMAILVERIFICATION_OTP_DISPATCH_REQUESTED"


    def __init__(self, db_session: AsyncSession):
        self._db_session = db_session
        self.security_repo = SecuritySQLAlchemyRepository(db_session)
        self.outbox_repo = OutboxEventsSQLAlchemyRepository(db_session)
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

    
        try:

            # extra user-level rate limit (in addition to IP)
            user_rate_key = f"user:emailverification:requestotp:{user_id}"
            user_allowed_request = await rate_limiter.check_window_limit(
                key=user_rate_key,
                limit=settings.EMAILVERIFICATION_OTP_USER_RATE_LIMIT,
                window=settings.EMAILVERIFICATION_OTP_USER_RATE_WINDOW_SECONDS,
            )
            if not user_allowed_request:
                return standardize_response(
                    status_code=429,
                    messages=["Too many OTP requests for this user. Please try again later."],
                )
            
            channel = (channel or "").strip().upper()
            if channel != "EMAIL":
                return standardize_response(status_code=400, messages=["channel must be EMAIL"])

            user = await self.security_repo.get_active_user(user_id)
            if not user:
                return standardize_response(status_code=404, messages=["User not found for email verification"])

            if user.is_email_verified == "Y":
                return standardize_response(status_code=400, messages=["Email already verified"])

            destination_raw = user.email
            destination_masked = self._mask_email(user.email)
            now = now_ist()

            # Cooldown + one-active policy
            active_otp_challenge = await self.security_repo.get_latest_active_otp_challenge(
                user_id=user_id,
                purpose=self.OTP_PURPOSE_EMAIL_VERIFICATION,
                channel="EMAIL",
                now_time=now,
            )
            if active_otp_challenge:
                elapsed_seconds = int((now - active_otp_challenge.created_at).total_seconds())
                if elapsed_seconds < self.OTP_REQUEST_COOLDOWN_SECONDS:
                    retry_after_seconds = self.OTP_REQUEST_COOLDOWN_SECONDS - elapsed_seconds
                    return standardize_response(
                        status_code=429,
                        messages=[f"OTP already requested. Please retry after {retry_after_seconds} seconds"],
                        data={
                            "retry_after_seconds": retry_after_seconds,
                            "challenge_id": active_otp_challenge.challenge_id,
                        },
                    )    
                expires_in_sec = max(0, int((active_otp_challenge.expires_at - now).total_seconds()))
                return standardize_response(
                    status_code=200,
                    messages=[f"OTP request is already accepted"],
                    data={
                        "challenge_id": active_otp_challenge.challenge_id,
                        "expires_in_sec": expires_in_sec,
                        "destination_masked": active_otp_challenge.destination_masked,
                        "dispatch_status": "already_active",
                    }
                )
            
            otp = self._generate_otp()
            otp_hash = self._hash_otp(otp)
            otp_ciphertext = self._encrypt_otp(otp)
            challenge_id = self._build_challenge_id(user_id)
            expires_at = now + timedelta(seconds=self.OTP_TTL_SECONDS)
                    
            await self.security_repo.add_otp_challenge(
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

            await self.outbox_repo.add_outbox_event(
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

            await self.security_repo.add_security_event(
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

            await self._db_session.commit()

            return standardize_response(
                status_code=200,
                messages=[f"OTP request accepted"],
                data={
                    "challenge_id": challenge_id,
                    "expires_in_sec": self.OTP_TTL_SECONDS,
                    "destination_masked": destination_masked,
                    "dispatch_status": "accepted",
                }
            )

        except BaseAppException as e:
            await self._db_session.rollback()
            raise e
        
        except Exception as e:
            await self._db_session.rollback()
            return standardize_response(
                status_code=500,
                messages=[f"{str(e)}"]
            )


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
            
            # Extra user-level rate limit (in addition to route IP-based limit)
            user_rate_key = f"user:emailverification:requestotp:confirm:{user_id}"
            user_allowed_request = await rate_limiter.check_window_limit(
                key=user_rate_key,
                limit=settings.EMAILVERIFICATION_CONFIRM_USER_RATE_LIMIT,
                window=settings.EMAILVERIFICATION_CONFIRM_USER_RATE_WINDOW_SECONDS,
            )
            if not user_allowed_request:
                return standardize_response(
                    status_code=429,
                    messages=["Too many email verification confirm attempts for this user. Please try again later."],
                )
            
            challenge = await self.security_repo.get_otp_challenge_for_update(
                challenge_id=challenge_id,
                user_id=user_id,
                purpose=self.OTP_PURPOSE_EMAIL_VERIFICATION,
            )
            if not challenge:
                return standardize_response(status_code=400, messages=["Invalid OTP challenge"])

            now = now_ist()

            if challenge.status == self.OTP_STATUS_VERIFIED:
                return standardize_response(status_code=400, messages=["OTP already used"])

            # boundary-safe expiry check
            if challenge.expires_at <= now:
                challenge.status = self.OTP_STATUS_EXPIRED
                challenge.last_error_code = "OTP_EXPIRED"
                challenge.updated_at = now
                await self.security_repo.add_security_event(
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
                await self._db_session.commit()
                return standardize_response(status_code=400, messages=["OTP expired"])

            if challenge.attempts_used >= challenge.max_attempts:
                challenge.status = self.OTP_STATUS_BLOCKED
                challenge.last_error_code = "OTP_ATTEMPTS_EXCEEDED"
                challenge.updated_at = now
                await self._db_session.commit()
                return standardize_response(status_code=400, messages=["OTP attempts exceeded"])

            if not self._verify_otp(otp=otp, otp_hash=challenge.otp_hash):
                challenge.attempts_used += 1
                challenge.updated_at = now
                challenge.last_error_code = "OTP_INVALID"
                if challenge.attempts_used >= challenge.max_attempts:
                    challenge.status = self.OTP_STATUS_BLOCKED

                await self.security_repo.add_security_event(
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
                await self._db_session.commit()
                return standardize_response(status_code=400, messages=["Invalid OTP"])

            verified_at = now_ist()
            updated = await self.security_repo.mark_user_email_verified(
                user_id=user_id,
                verified_at=verified_at,
            )
            if not updated:
                await self._db_session.rollback()
                return standardize_response(status_code=404, messages=["User not found"])

            challenge.attempts_used += 1
            challenge.status = self.OTP_STATUS_VERIFIED
            challenge.last_error_code = None
            challenge.updated_at = verified_at

            await self.security_repo.add_security_event(
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

            await self.security_repo.add_security_event(
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

            await self._db_session.commit()

            # removing from cache
            cacheKey = f"user:profile:{user_id}"
            await cache_delete(cacheKey)
            
            return standardize_response(
                status_code=200,
                messages=[f"Email verified successfully"],
                data={
                    "email_verified": True
                }
            )
        
        except BaseAppException as e:
            await self._db_session.rollback()
            raise e
        
        except Exception as e:
            await self._db_session.rollback()
            return standardize_response(
                status_code=500,
                messages=[f"{str(e)}"]
            )

        


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
