
from datetime import timedelta
import random
from app.common.utils.datetime import now_ist
from app.core.settings import get_settings
from app.infrastructure.outbox.retry_handlers.outbox_base_retryhandler import OutboxBaseRetryHandler

settings = get_settings()

class MasterDataSchedulesOutboxRetryHandler(OutboxBaseRetryHandler):

    def __init__(self, **kwargs):
        self.outbox_repo = kwargs.get("outbox_repo", None)


    async def handle(self, **kwargs):

        event = kwargs.get("event", None)
        error_message = kwargs.get("error_message", "")

        now = now_ist()
        retry_count_after = int(event.retry_count) + 1
        max_retries = int(settings.MASTERDATA_SCHEDULE_CREATED)

        if retry_count_after>=max_retries:
            await self.outbox_repo.mark_outbox_failed(
                event=event, last_error=error_message, updated_at=now,
            )
        else:
            backoff_base = min(300, 2 ** min(retry_count_after, 8))
            backoff_jitter = random.randint(0, 5)
            next_retry_at = now + timedelta(seconds=backoff_base + backoff_jitter)
            await self.outbox_repo.mark_outbox_retry(
                event=event, next_retry_at=next_retry_at, last_error=error_message, updated_at=now,
            )