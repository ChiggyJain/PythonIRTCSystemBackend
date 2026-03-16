
"""
Factory for OTP sender providers.
"""

from app.core.settings import get_settings
from app.domains.security.providers.base import (
    EmailOtpSenderBase,
    SmsOtpSenderBase,
)
from app.infrastructure.email.sendgrid_otp_sender import SendGridEmailOtpSender
from app.infrastructure.sms.noop_sms_otp_sender import NoopSmsOtpSender


_settings = get_settings()
_email_sender: EmailOtpSenderBase | None = None
_sms_sender: SmsOtpSenderBase | None = None


def get_email_otp_sender() -> EmailOtpSenderBase:
    global _email_sender

    if _email_sender is not None:
        return _email_sender

    provider = _settings.PWDCHANGED_OTP_EMAIL_PROVIDER.strip().upper()
    if provider == "SENDGRID":
        _email_sender = SendGridEmailOtpSender(
            api_key=_settings.SENDGRID_API_KEY,
            from_email=_settings.PWDCHANGED_PWDCHANGED_OTP_FROM_EMAIL,
            subject_prefix=_settings.PWDCHANGED_OTP_EMAIL_SUBJECT_PREFIX,
        )
        return _email_sender

    raise RuntimeError(f"Unsupported OTP email provider: {provider}")


def get_sms_otp_sender() -> SmsOtpSenderBase:
    global _sms_sender

    if _sms_sender is not None:
        return _sms_sender

    provider = _settings.PWDCHANGED_OTP_SMS_PROVIDER.strip().upper()
    if provider == "NONE":
        _sms_sender = NoopSmsOtpSender()
        return _sms_sender

    # Keep placeholder for future providers like MSG91/Twilio.
    raise RuntimeError(f"Unsupported OTP SMS provider: {provider}")
