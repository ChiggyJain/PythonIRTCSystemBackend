
"""
SendGrid implementation for email OTP sender.
"""

import asyncio
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from app.domains.security.providers.base import (
    EmailOtpSenderBase,
    OtpSendResult,
)


class SendGridEmailOtpSender(EmailOtpSenderBase):

    def __init__(
        self,
        *,
        api_key: str,
        from_email: str,
        subject_prefix: str,
    ):
        self._provider = "SENDGRID"
        self._from_email = from_email
        self._subject_prefix = subject_prefix
        self._client = SendGridAPIClient(api_key=api_key)

    async def send_otp(
        self,
        *,
        to_email: str,
        otp: str,
        purpose: str,
        challenge_id: str,
    ) -> OtpSendResult:

        ## for testing purpose only
        print(f"challenge_id: {challenge_id}, OTP: {otp}")    
        return OtpSendResult(
            accepted=True,
            provider=self._provider,
            provider_message_id="TestEmailMsgId",
        )
    
        subject = f"{self._subject_prefix} OTP"
        content = (
            f"Your OTP is {otp}. "
            f"Purpose: {purpose}. "
            f"Challenge: {challenge_id}. "
            f"This OTP expires in 5 minutes."
        )

        msg = Mail(
            from_email=self._from_email,
            to_emails=to_email,
            subject=subject,
            plain_text_content=content,
        )

        try:
            response = await asyncio.to_thread(self._client.send, msg)
            accepted = response.status_code in (200, 202)
            message_id = None
            if hasattr(response, "headers") and response.headers:
                message_id = response.headers.get("X-Message-Id")

            if accepted:
                return OtpSendResult(
                    accepted=True,
                    provider=self._provider,
                    provider_message_id=message_id,
                )

            return OtpSendResult(
                accepted=False,
                provider=self._provider,
                provider_message_id=message_id,
                error_code="SENDGRID_REJECTED",
                error_message=f"sendgrid status code={response.status_code}",
            )

        except Exception as exc:
            return OtpSendResult(
                accepted=False,
                provider=self._provider,
                error_code="SENDGRID_EXCEPTION",
                error_message=str(exc),
            )
