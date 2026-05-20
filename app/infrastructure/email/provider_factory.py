
from app.core.settings import get_settings
from app.infrastructure.email.base import (
    EmailSenderBase,
    SmsOtpSenderBase,
)
from app.infrastructure.email.sendgrid_email_sender import (
    SendGridEmailSender,
)


_settings = get_settings()


_pwdchanged_email_sender_instances: EmailSenderBase | None = None
_emailverification_email_sender_instances: EmailSenderBase | None = None
_emailchanged_email_sender_instances: EmailSenderBase | None = None
_booking_updated_status_email_sender_instances: EmailSenderBase | None = None



def get_pwdchanged_email_otp_sender() -> EmailSenderBase:
    global _pwdchanged_email_sender_instances
    if _pwdchanged_email_sender_instances is not None:
        return _pwdchanged_email_sender_instances
    provider = _settings.PWDCHANGED_OTP_EMAIL_PROVIDER.strip().upper()
    if provider == "SENDGRID":
        _pwdchanged_email_sender_instances = SendGridEmailSender(
            api_key=_settings.SENDGRID_API_KEY,
            from_email=_settings.PWDCHANGED_OTP_FROM_EMAIL,
            dry_run=_settings.SENDGRID_DRY_RUN,
        )
        return _pwdchanged_email_sender_instances
    raise RuntimeError(f"Unsupported PWDCHANGED OTP email provider: {provider}")


def get_emailverification_email_otp_sender() -> EmailSenderBase:
    global _emailverification_email_sender_instances
    if _emailverification_email_sender_instances is not None:
        return _emailverification_email_sender_instances
    provider = _settings.EMAILVERIFICATION_OTP_EMAIL_PROVIDER.strip().upper()
    if provider == "SENDGRID":
        _emailverification_email_sender_instances = SendGridEmailSender(
            api_key=_settings.SENDGRID_API_KEY,
            from_email=_settings.EMAILVERIFICATION_OTP_FROM_EMAIL,
            dry_run=_settings.SENDGRID_DRY_RUN,
        )
        return _emailverification_email_sender_instances
    raise RuntimeError(f"Unsupported EMAILVERIFICATION OTP email provider: {provider}")


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