
from typing import Any
import asyncio
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from app.infrastructure.email.base import (
    EmailSenderBase,
    EmailSendResult,
)


class SendGridEmailSender(EmailSenderBase):

    def __init__(
        self,
        *,
        api_key: str,
        from_email: str,
        dry_run: bool = False,
    ):
        self._provider = "SENDGRID"
        self._from_email = from_email
        self._dry_run = dry_run
        self._client = SendGridAPIClient(api_key=api_key)

    async def send_email(
        self,
        *,
        to_email: str,
        subject: str,
        plain_text_content: str | None = None,
        html_content: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> EmailSendResult:

        if self._dry_run:
            print(f"Dry run: Would send email to {to_email} with subject '{subject}'")
            return EmailSendResult(
                accepted=True,
                provider=self._provider,
                provider_message_id="dry-run",
            )

        msg = Mail(
            from_email=self._from_email,
            to_emails=to_email,
            subject=subject,
        )

        if plain_text_content:
            msg.plain_text_content = plain_text_content
        if html_content:
            msg.html_content = html_content

        try:
            
            response = await asyncio.to_thread(self._client.send, msg)
            print(f"response: {response}")
            accepted = response.status_code in (200, 202)
            message_id = None
            if hasattr(response, "headers") and response.headers:
                message_id = response.headers.get("X-Message-Id")

            if accepted:
                return EmailSendResult(
                    accepted=True,
                    provider=self._provider,
                    provider_message_id=message_id,
                )

            return EmailSendResult(
                accepted=False,
                provider=self._provider,
                provider_message_id=message_id,
                error_code="SENDGRID_REJECTED",
                error_message=f"sendgrid status code={response.status_code}",
            )

        except Exception as exc:
            return EmailSendResult(
                accepted=False,
                provider=self._provider,
                error_code="SENDGRID_EXCEPTION",
                error_message=str(exc),
            )