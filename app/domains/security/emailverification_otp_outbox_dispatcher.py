
"""
Email Verification OTP Outbox -> Kafka publisher.
Only handles event_type = EMAILVERIFICATION_OTP_DISPATCH_REQUESTED_V1.
"""

from datetime import timedelta
import json
from aiokafka import AIOKafkaProducer
from app.common.utils.datetime import now_ist
from app.core.settings import get_settings
from app.domains.security.repository.base import SecurityRepositoryBase


settings = get_settings()


class EmailVerificationOTPOutboxDispatcher:
    
    OTP_EVENT_TYPE = "EMAILVERIFICATION_OTP_DISPATCH_REQUESTED_V1"

    def __init__(self, *, repo: SecurityRepositoryBase, producer: AIOKafkaProducer):
        self.repo = repo
        self.producer = producer

    async def process_batch(self, *, batch_size: int = 100) -> dict:
        now = now_ist()
        events = await self.repo.fetch_pending_outbox_events(
            event_type=self.OTP_EVENT_TYPE,
            limit=batch_size,
            now_time=now,
        )

        stats = {"processed": 0, "published": 0, "failed": 0}

        for event in events:
            stats["processed"] += 1
            payload = event.payload_json or {}
            user_id = int(payload.get("user_id") or 0)

            try:
                message = json.dumps(
                    {"outbox_id": event.id, "event_type": event.event_type, **payload},
                    separators=(",", ":"),
                ).encode("utf-8")

                key = str(payload.get("user_id", "0")).encode("utf-8")
                await self.producer.send_and_wait(
                    topic=settings.EMAILVERIFICATION_OTP_DISPATCH_TOPIC,
                    key=key,
                    value=message,
                )

                await self.repo.mark_outbox_published(event=event, published_at=now_ist())
                await self.repo.commit()
                stats["published"] += 1

            except Exception as exc:
                retry_count_after = int(event.retry_count) + 1
                max_retries = int(settings.EMAILVERIFICATION_OTP_OUTBOX_MAX_RETRIES)
                now_retry = now_ist()

                if retry_count_after >= max_retries:
                    await self.repo.mark_outbox_failed(
                        event=event,
                        last_error=str(exc),
                        updated_at=now_retry,
                    )
                else:
                    backoff = min(300, 2 ** min(retry_count_after, 8))
                    await self.repo.mark_outbox_retry(
                        event=event,
                        next_retry_at=now_retry + timedelta(seconds=backoff),
                        last_error=str(exc),
                        updated_at=now_retry,
                    )

                if user_id > 0:
                    await self.repo.add_security_event(
                        user_id=user_id,
                        event_name="email_verification_outbox_publish_failed",
                        event_category="OUTBOX",
                        channel="EMAIL",
                        provider="KAFKA",
                        status="failed",
                        reason_code="KAFKA_PUBLISH_FAILED",
                        correlation_id=None,
                        request_id=None,
                        ip_address=None,
                        user_agent=None,
                        metadata_json={"outbox_id": event.id, "error": str(exc)[:500]},
                    )

                await self.repo.commit()
                stats["failed"] += 1

        return stats
