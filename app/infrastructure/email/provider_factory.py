
from app.core.settings import get_settings
from app.infrastructure.email.base import (
    EmailSenderBase,
    EmailOtpSenderBase,
    SmsOtpSenderBase,
)
from app.infrastructure.email.sendgrid_email_sender import (
    SendGridEmailSender,
)
from app.infrastructure.email.sendgrid_otp_sender import (
    SendGridEmailOtpSender,
)
from app.infrastructure.sms.noop_sms_otp_sender import (
    NoopSmsOtpSender
)


_settings = get_settings()


_sms_sender: SmsOtpSenderBase | None = None
_pwdchanged_email_sender: EmailOtpSenderBase | None = None
_emailverification_email_sender: EmailOtpSenderBase | None = None
_emailchanged_email_sender_instances: EmailSenderBase | None = None
_booking_updated_status_email_sender_instances: EmailSenderBase | None = None


def get_pwdchanged_sms_otp_sender() -> SmsOtpSenderBase:
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


"""
def get_emailchanged_email_otp_sender() -> EmailOtpSenderBase:
    global _emailchanged_email_sender_instances
    if _emailchanged_email_sender_instances is not None:
        return _emailchanged_email_sender_instances
    provider = _settings.EMAILCHANGED_OTP_EMAIL_PROVIDER.strip().upper()
    if provider == "SENDGRID":
        _emailchanged_email_sender_instances = SendGridEmailOtpSender(
            api_key=_settings.SENDGRID_API_KEY,
            from_email=_settings.EMAILCHANGED_OTP_FROM_EMAIL,
            subject_prefix=_settings.EMAILCHANGED_OTP_EMAIL_SUBJECT_PREFIX,
        )
        return _emailchanged_email_sender_instances
    raise RuntimeError(f"Unsupported EMAILCHANGED OTP email provider: {provider}")
"""

def get_emailchanged_email_otp_sender() -> EmailSenderBase:
    global _emailchanged_email_sender_instances
    if _emailchanged_email_sender_instances is not None:
        return _emailchanged_email_sender_instances
    provider = _settings.EMAILCHANGED_OTP_EMAIL_PROVIDER.strip().upper()
    if provider == "SENDGRID":
        _emailchanged_email_sender_instances = SendGridEmailSender(
            api_key=_settings.SENDGRID_API_KEY,
            from_email=_settings.EMAILCHANGED_OTP_FROM_EMAIL,
            dry_run=_settings.SENDGRID_DRY_RUN,
        )
        return _emailchanged_email_sender_instances
    raise RuntimeError(f"Unsupported EMAILCHANGED OTP email provider: {provider}")



def get_booking_updated_status_email_sender() -> EmailSenderBase:
    global _booking_updated_status_email_sender_instances
    if _booking_updated_status_email_sender_instances is not None:
        return _booking_updated_status_email_sender_instances
    provider = _settings.BOOKING_UPDATED_STATUS_EMAIL_PROVIDER.strip().upper()
    if provider == "SENDGRID":
        _booking_updated_status_email_sender_instances = SendGridEmailSender(
            api_key=_settings.SENDGRID_API_KEY,
            from_email=_settings.BOOKING_UPDATED_STATUS_FROM_EMAIL,
            dry_run=_settings.SENDGRID_DRY_RUN,
        )
        return _booking_updated_status_email_sender_instances
    raise RuntimeError(f"Unsupported BOOKING email provider: {provider}")