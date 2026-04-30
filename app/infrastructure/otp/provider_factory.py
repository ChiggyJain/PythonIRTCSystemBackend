
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
_pwdchanged_email_sender: EmailOtpSenderBase | None = None
_emailverification_email_sender: EmailOtpSenderBase | None = None
_emailchanged_email_sender: EmailOtpSenderBase | None = None



def get_sms_otp_sender() -> SmsOtpSenderBase:
    global _sms_sender
    if _sms_sender is not None:
        return _sms_sender
    provider = _settings.PWDCHANGED_OTP_SMS_PROVIDER.strip().upper()
    if provider == "NONE":
        _sms_sender = NoopSmsOtpSender()
        return _sms_sender
    raise RuntimeError(f"Unsupported OTP SMS provider: {provider}")



def get_pwdchanged_email_otp_sender() -> EmailOtpSenderBase:
    global _pwdchanged_email_sender
    if _pwdchanged_email_sender is not None:
        return _pwdchanged_email_sender
    provider = _settings.PWDCHANGED_OTP_EMAIL_PROVIDER.strip().upper()
    if provider == "SENDGRID":
        _pwdchanged_email_sender = SendGridEmailOtpSender(
            api_key=_settings.SENDGRID_API_KEY,
            from_email=_settings.EMAILCHANGED_OTP_FROM_EMAIL,
            subject_prefix=_settings.EMAILCHANGED_OTP_EMAIL_SUBJECT_PREFIX,
        )
        return _pwdchanged_email_sender
    raise RuntimeError(f"Unsupported PWDCHANGED OTP email provider: {provider}")


def get_emailverification_email_otp_sender() -> EmailOtpSenderBase:
    global _emailverification_email_sender
    if _emailverification_email_sender is not None:
        return _emailverification_email_sender
    provider = _settings.EMAILVERIFICATION_OTP_EMAIL_PROVIDER.strip().upper()
    if provider == "SENDGRID":
        _emailverification_email_sender = SendGridEmailOtpSender(
            api_key=_settings.SENDGRID_API_KEY,
            from_email=_settings.EMAILVERIFICATION_OTP_FROM_EMAIL,
            subject_prefix=_settings.EMAILVERIFICATION_OTP_EMAIL_SUBJECT_PREFIX,
        )
        return _emailverification_email_sender
    raise RuntimeError(f"Unsupported EMAILVERIFICATION OTP email provider: {provider}")


def get_emailchanged_email_otp_sender() -> EmailOtpSenderBase:
    global _emailchanged_email_sender
    if _emailchanged_email_sender is not None:
        return _emailchanged_email_sender
    provider = _settings.EMAILCHANGED_OTP_EMAIL_PROVIDER.strip().upper()
    if provider == "SENDGRID":
        _emailchanged_email_sender = SendGridEmailOtpSender(
            api_key=_settings.SENDGRID_API_KEY,
            from_email=_settings.EMAILCHANGED_OTP_FROM_EMAIL,
            subject_prefix=_settings.EMAILCHANGED_OTP_EMAIL_SUBJECT_PREFIX,
        )
        return _emailchanged_email_sender
    raise RuntimeError(f"Unsupported EMAILCHANGED OTP email provider: {provider}")
