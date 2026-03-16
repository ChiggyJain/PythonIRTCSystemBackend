
"""
SMS sender placeholder until real provider integration is added.
"""

from app.domains.security.providers.base import (
    SmsOtpSenderBase,
    OtpSendResult,
)


class NoopSmsOtpSender(SmsOtpSenderBase):

    async def send_otp(
        self,
        *,
        to_mobile: str,
        otp: str,
        purpose: str,
        challenge_id: str,
    ) -> OtpSendResult:

        return OtpSendResult(
            accepted=False,
            provider="SMS_NONE",
            error_code="SMS_PROVIDER_NOT_CONFIGURED",
            error_message="SMS provider is not configured",
        )
