"""
EMAIL CHANGED OTP outbox publisher.
Only handles: EMAILCHANGED_OTP_DISPATCH_REQUESTED_V1
"""

from datetime import timedelta
import json
import random
from aiokafka import AIOKafkaProducer
from app.common.utils.datetime import now_ist
from app.core.settings import get_settings
from app.domains.security.repository.base import SecurityRepositoryBase


settings = get_settings()


class EmailChangedOTPOutboxDispatcher:
    OTP_EVENT_TYPE = "EMAILCHANGED_OTP_DISPATCH_REQUESTED_V1"

    def __init__(self, *, repo: SecurityRepositoryBase, producer: AIOKafkaProducer):
        self.repo = repo
        self.producer = producer

    async def process_batch(self, *, batch_size: int = 100) -> dict:
        stats = {"processed": 0, "published": 0, "failed": 0, "skipped": 0}

        for _ in range(batch_size):
            now = now_ist()
            events = await self.repo.fetch_pending_outbox_events(
                event_type=self.OTP_EVENT_TYPE,
                limit=1,
                now_time=now,
            )
            if not events:
                break

            event = events[0]
            stats["processed"] += 1
            payload = event.payload_json or {}
            user_id = self._safe_int(payload.get("user_id"), default=0)

            try:
                topic = self._topic_for_event(event.event_type)
                if not topic:
                    raise ValueError(f"unsupported event_type={event.event_type}")

                message = json.dumps(
                    {"outbox_id": event.id, "event_type": event.event_type, **payload},
                    separators=(",", ":"),
                ).encode("utf-8")

                key = str(user_id if user_id > 0 else 0).encode("utf-8")

                md = await self.producer.send_and_wait(
                    topic=topic,
                    key=key,
                    value=message,
                )

                published_at = now_ist()
                await self.repo.mark_outbox_published(event=event, published_at=published_at)

                if user_id > 0:
                    await self.repo.add_security_event(
                        user_id=user_id,
                        event_name="email_change_outbox_published",
                        event_category="OUTBOX",
                        channel="EMAIL",
                        provider="KAFKA",
                        status="published",
                        reason_code=None,
                        correlation_id=None,
                        request_id=None,
                        ip_address=None,
                        user_agent=None,
                        metadata_json={
                            "outbox_id": event.id,
                            "topic": md.topic,
                            "partition": md.partition,
                            "offset": md.offset,
                        },
                    )

                await self.repo.commit()
                stats["published"] += 1

            except Exception as exc:
                await self._mark_retry_or_failed(
                    event=event,
                    user_id=user_id,
                    error_message=str(exc),
                )
                stats["failed"] += 1

        return stats

    async def _mark_retry_or_failed(
        self,
        *,
        event,
        user_id: int,
        error_message: str,
    ) -> None:
        now = now_ist()
        retry_count_after = int(event.retry_count) + 1
        max_retries = int(settings.EMAILCHANGED_OTP_OUTBOX_MAX_RETRIES)

        try:
            if retry_count_after >= max_retries:
                await self.repo.mark_outbox_failed(
                    event=event,
                    last_error=error_message,
                    updated_at=now,
                )
                outbox_status = "failed"
            else:
                backoff_base = min(300, 2 ** min(retry_count_after, 8))
                backoff_jitter = random.randint(0, 5)
                next_retry_at = now + timedelta(seconds=backoff_base + backoff_jitter)

                await self.repo.mark_outbox_retry(
                    event=event,
                    next_retry_at=next_retry_at,
                    last_error=error_message,
                    updated_at=now,
                )
                outbox_status = "retry_scheduled"

            if user_id > 0:
                await self.repo.add_security_event(
                    user_id=user_id,
                    event_name="email_change_outbox_publish_failed",
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

            await self.repo.commit()

        except Exception:
            await self.repo.rollback()

    def _topic_for_event(self, event_type: str) -> str | None:
        if event_type == self.OTP_EVENT_TYPE:
            return settings.EMAILCHANGED_OTP_DISPATCH_TOPIC
        return None

    @staticmethod
    def _safe_int(value: object, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
