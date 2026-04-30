
from datetime import timedelta
import random
from app.common.utils.datetime import now_ist
from app.core.settings import get_settings
from app.infrastructure.outbox.retry_handlers.outbox_base_retryhandler import OutboxBaseRetryHandler

settings = get_settings()

class PwdChangedOtpOutboxRetryHandler(OutboxBaseRetryHandler):

    def __init__(self, **kwargs):
        self.outbox_repo = kwargs.get("outbox_repo", None)
        self.security_repo = kwargs.get("security_repo", None)


    async def handle(self, **kwargs):

        event = kwargs.get("event", None)
        user_id = int(kwargs.get("user_id", 0))
        error_message = kwargs.get("error_message", "")

        now = now_ist()
        retry_count_after = int(event.retry_count) + 1
        max_retries = int(settings.PWDCHANGED_OTP_OUTBOX_MAX_RETRIES)

        if retry_count_after>=max_retries:
            await self.outbox_repo.mark_outbox_failed(
                event=event, last_error=error_message, updated_at=now,
            )
            outbox_status = "failed"
        else:
            backoff_base = min(300, 2 ** min(retry_count_after, 8))
            backoff_jitter = random.randint(0, 5)
            next_retry_at = now + timedelta(seconds=backoff_base + backoff_jitter)
            await self.outbox_repo.mark_outbox_retry(
                event=event, next_retry_at=next_retry_at, last_error=error_message, updated_at=now,
            )
            outbox_status = "retry_scheduled"

        # logging
        if self.security_repo and user_id > 0:
            await self.security_repo.add_security_event(
                user_id=user_id,
                event_name="pwd_change_outbox_publish_failed",
                event_category="OUTBOX",
                channel="EMAIL",
                provider="KAFKA",
                status=outbox_status,
                reason_code="KAFKA_PUBLISH_FAILED",
                correlation_id=None,
                request_id=None,
                ip_address=None,
                user_agent=None,
                metadata_json={
                    "outbox_id": event.id,
                    "retry_count": retry_count_after,
                    "error": error_message[:500],
                },
            )