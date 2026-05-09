
from anyio import to_thread
from datetime import timedelta
import base64
import hashlib
import hmac
import secrets
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.utils.logger import app_logger
from app.common.utils.datetime import now_ist
from app.common.utils.password import hash_password
from app.core.exceptions import BaseAppException
from app.core.response import (
    success_response, 
    error_response,
    exception_response
)
from app.core.settings import get_settings
from app.common.utils.ratelimiter import rate_limiter
from app.domains.security.repository.sqlalchemy_repo import SecuritySQLAlchemyRepository
from app.infrastructure.outbox.repository.sqlalchemy_repo import OutboxEventsSQLAlchemyRepository
from app.common.cache.redis_cache import(
    build_cache_key, 
    cache_delete,
    build_cache_set_key, 
    cache_set_members, 
    cache_set_delete
)


settings = get_settings()


class PasswordChangeOtpService:

    OTP_PURPOSE_PASSWORD_CHANGE = "PASSWORD_CHANGE"
    OTP_STATUS_REQUESTED = "REQUESTED"
    OTP_STATUS_SENT = "SENT"
    OTP_STATUS_VERIFIED = "VERIFIED"
    OTP_STATUS_EXPIRED = "EXPIRED"
    OTP_STATUS_BLOCKED = "BLOCKED"
    OTP_TTL_SECONDS = 300
    OTP_MAX_ATTEMPTS = 5
    OTP_REQUEST_COOLDOWN_SECONDS = 60
    OTP_CIPHER_KEY_VERSION = "v1"
    OUTBOX_STATUS_PENDING = "PENDING"
    OUTBOX_EVENT_TYPE = "PWDCHANGED_OTP_DISPATCH_REQUESTED"


    def __init__(self, db_session: AsyncSession):
        self._db_session = db_session
        self.security_repo = SecuritySQLAlchemyRepository(db_session)
        self.outbox_repo = OutboxEventsSQLAlchemyRepository(db_session)
        self._otp_hash_secret = f"{settings.JWT_SECRET_KEY}:otp-hash:v1"
        self._fernet = self._build_fernet(
            secret=f"{settings.JWT_SECRET_KEY}:otp-cipher:v1"
        )


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

        try:

            # extra user-level rate limit (in addition to IP)
            cacheKey = f"user:passwordchange:requestotp:{user_id}"
            user_allowed_request = await rate_limiter.check_window_limit(
                key=cacheKey,
                limit=settings.PWDCHANGED_OTP_USER_RATE_LIMIT,
                window=settings.PWDCHANGED_OTP_USER_RATE_WINDOW_SECONDS,
            )
            if not user_allowed_request:
                return error_response(
                    status_code=429,
                    messages=["Too many OTP requests for this user. Please try again later."],
                )
        
        
            # normalize the channel (EMAIL/MOBILE)
            channel = self._normalize_channel(channel)

            # fetching active user details
            user = await self.security_repo.get_active_user(user_id)
            if not user:
                return error_response(
                    status_code=404,
                    messages=["User not found"],
                )  
            if user.is_mobile_verified == "N":
                print(f"In future we have to check mobile is verified or not. Pending-Task")
            if user.is_email_verified == "N":
                return error_response(
                    status_code=401,
                    messages=["Password change process is not allow without verifying email"],
                )

            # making masked string of channel (EMAIL/MOBILE)
            destination_raw, destination_masked = self._get_destination(
                channel=channel,
                email=user.email,
                mobile=user.mobile,
            )

            # generating the random six-digits OTP and I think we can move this functions in app/common/utils folder
            otp = self._generate_otp()

            # generating the hashed-number of OTP and I think we can move this functions in app/common/utils folder
            otp_hash = self._hash_otp(otp)

            # generating the cipher-text of OTP and I think we can move this functions in app/common/utils folder
            otp_ciphertext = self._encrypt_otp(otp)

            # challengeId is generating
            challenge_id = self._build_challenge_id(user_id)

            now = now_ist()
            expires_at = now + timedelta(seconds=self.OTP_TTL_SECONDS)

            
            # Cooldown + one-active policy
            # Rule:
            # 1) If active challenge exists and requested very recently -> block (429)
            # 2) If active challenge exists and cooldown passed -> reuse existing challenge
            active_otp_challenge = await self.security_repo.get_latest_active_otp_challenge(
                user_id=user_id,
                purpose=self.OTP_PURPOSE_PASSWORD_CHANGE,
                channel=channel,
                now_time=now,
            )
            if active_otp_challenge:
                elapsed_seconds = int((now - active_otp_challenge.created_at).total_seconds())
                if elapsed_seconds < self.OTP_REQUEST_COOLDOWN_SECONDS:
                    retry_after_seconds = self.OTP_REQUEST_COOLDOWN_SECONDS - elapsed_seconds
                    return error_response(
                        status_code=429,
                        messages=[f"OTP already requested. Please retry after {retry_after_seconds} seconds"],
                        data={
                            "retry_after_seconds": retry_after_seconds,
                            "challenge_id": active_otp_challenge.challenge_id,
                        },
                    )
                # Reuse current active challenge instead of creating another row.
                expires_in_sec = max(0, int((active_otp_challenge.expires_at - now).total_seconds()))
                return success_response(
                    status_code=200,
                    messages=[f"OTP request is already accepted"],
                    data={
                        "challenge_id": active_otp_challenge.challenge_id,
                        "expires_in_sec": expires_in_sec,
                        "destination_masked": active_otp_challenge.destination_masked,
                        "dispatch_status": "already_active",
                    }
                )
            
            # adding otp details
            await self.security_repo.add_otp_challenge(
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

            # Outbox event only (Kafka publish is separate step independent worker)
            await self.outbox_repo.add_outbox_event(
                aggregate_type="OTP_CHALLENGE",
                aggregate_id=challenge_id,
                event_type=self.OUTBOX_EVENT_TYPE,
                payload_json={
                    "challenge_id": challenge_id,
                    "user_id": user_id,
                    "purpose": self.OTP_PURPOSE_PASSWORD_CHANGE,
                    "channel": channel,
                    "destination": destination_raw,
                },
                status=self.OUTBOX_STATUS_PENDING,
            )

            # adding logs into respective table
            await self.security_repo.add_security_event(
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

            await self._db_session.commit()

            return success_response(
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
            return exception_response(
                status_code=500,
                messages=[f"{str(e)}"],
            )


    
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

        try:

            # checking new password is match with confirm_password
            if new_password != confirm_password:
                raise error_response(
                    status_code=400,
                    messages=["password and confirm password must match"],
                )
            
            # Extra user-level rate limit (in addition to route IP-based limit)
            user_rate_key = f"user:passwordchange:requestotp:confirm:{user_id}"
            user_allowed = await rate_limiter.check_window_limit(
                key=user_rate_key,
                limit=settings.PWDCHANGED_CONFIRM_USER_RATE_LIMIT,
                window=settings.PWDCHANGED_CONFIRM_USER_RATE_WINDOW_SECONDS,
            )
            if not user_allowed:
                raise BaseAppException(
                    status_code=429,
                    messages=["Too many password change confirm attempts for this user. Please try again later."],
                )
            
    
            # fetching otp_challenge details
            challenge = await self.security_repo.get_otp_challenge_for_update(
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

                
            if challenge.expires_at <= now:
                challenge.status = self.OTP_STATUS_EXPIRED
                challenge.last_error_code = "OTP_EXPIRED"
                challenge.updated_at = now
                await self.security_repo.add_security_event(
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
                await self._db_session.commit()
                raise BaseAppException(
                    status_code=400,
                    messages=["OTP expired"],
                )

            if challenge.attempts_used >= challenge.max_attempts:
                challenge.status = self.OTP_STATUS_BLOCKED
                challenge.last_error_code = "OTP_ATTEMPTS_EXCEEDED"
                challenge.updated_at = now
                await self._db_session.commit()
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
                await self.security_repo.add_security_event(
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
                await self._db_session.commit()
                raise BaseAppException(
                    status_code=400,
                    messages=["Invalid OTP"],
                )

            changed_at = now_ist()

            # with this:
            # bcrypt hashing is CPU-bound, so run it in thread to avoid blocking event loop
            password_hash = await to_thread.run_sync(hash_password, new_password)

            updated = await self.security_repo.update_user_password(
                user_id=user_id,
                password_hash=password_hash,
                changed_at=changed_at,
            )
            if not updated:
                await self._db_session.rollback()
                raise BaseAppException(
                    status_code=404,
                    messages=["User not found"],
                )
            
            revoked_count = await self.security_repo.revoke_active_tokens_for_user(
                user_id=user_id,
                changed_at=changed_at,
            )

            challenge.attempts_used += 1
            challenge.status = self.OTP_STATUS_VERIFIED
            challenge.last_error_code = None
            challenge.updated_at = changed_at

            await self.security_repo.add_security_event(
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

            await self.security_repo.add_security_event(
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

            await self._db_session.commit()

            # 2) Cache cleanup as post-commit side-effect (best effort)
            user_index_key = build_cache_set_key(f"user:access:index:{user_id}")
            try:
                access_jti_set = await cache_set_members(key=user_index_key)
                for access_jti in access_jti_set:
                    access_key = build_cache_key(f"user:access:jti:{access_jti}")
                    try:
                        await cache_delete(key=access_key)
                    except Exception as exc:
                        app_logger.warning(
                            f"password_change cache_delete failed | user_id={user_id} | key={access_key} | error={str(exc)}"
                        )
                try:
                    await cache_set_delete(key=user_index_key)
                except Exception as exc:
                    app_logger.warning(
                        f"password_change cache_set_delete failed | user_id={user_id} | key={user_index_key} | error={str(exc)}"
                    )
            except Exception as exc:
                app_logger.error(
                    f"password_change cache_cleanup failed | user_id={user_id} | error={str(exc)}"
                )

        except BaseAppException:
            await self._db_session.rollback()
            raise
        except Exception:
            await self._db_session.rollback()
            raise

        return {
            "message": "Password changed successfully",
            "account_session_revoked_count": revoked_count,
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
        return f"PWDCHG_OTP_{user_id}_{ts}_{rand}"

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
