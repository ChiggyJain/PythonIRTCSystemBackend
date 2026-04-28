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
from app.infrastructure.outbox.repository.sqlalchemy_repo import OutboxEventsSQLAlchemyRepository

settings = get_settings()


class EmailChangedOTPOutboxDispatcher:

    OTP_EVENT_TYPE = "EMAILCHANGED_OTP_DISPATCH_REQUESTED_V1"


    def __init__(self, *, security_repo: SecurityRepositoryBase, outbox_events_repo: OutboxEventsSQLAlchemyRepository, producer: AIOKafkaProducer):
        self.security_repo = security_repo
        self.outbox_events_repo = outbox_events_repo
        self.producer = produceruser_id = self._safe_int(payload.get("user_id"), default=0)


    async def process_single_event(self) -> dict:

        # fetching pending/retry/ event details only
        now = now_ist()
        events = await self.outbox_events_repo.fetch_pending_outbox_events(
            event_type=self.OTP_EVENT_TYPE, limit=1, now_time=now,
        )
        if not events:
            return False

        event = events[0]
        payload = event.payload_json or {}
        user_id = self._safe_int(payload.get("user_id"), default=0)

        try:

            # getting topic-name based on event-type
            topic = self._topic_for_event(event.event_type)
            if not topic:
                raise ValueError(f"unsupported event_type={event.event_type}")

            # preparing message for publishing to the topic
            message = json.dumps(
                {"outbox_id": event.id, "event_type": event.event_type, **payload},
                separators=(",", ":"),
            ).encode("utf-8")

            # preparing key to used for publishing to the topic partition
            key = str(user_id if user_id > 0 else 0).encode("utf-8")
                
            # Kafka publish
            md = await self.producer.send_and_wait(topic=topic, key=key, value=message,)

            # updating status into outbox_events table
            published_at = now_ist()
            await self.outbox_events_repo.mark_outbox_published(event=event, published_at=published_at)

            # adding logs into security_event table
            if user_id > 0:
                await self.security_repo.add_security_event(
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

            return True
        
        except Exception as exc:
            # retry processing handling case
            await self._mark_retry_or_failed(
                event=event, user_id=user_id, error_message=str(exc),
            )
            return True 
    

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

            if retry_count_after>=max_retries:
                await self.outbox_events_repo.mark_outbox_failed(
                    event=event, last_error=error_message, updated_at=now,
                )
                outbox_status = "failed"
            else:
                backoff_base = min(300, 2 ** min(retry_count_after, 8))
                backoff_jitter = random.randint(0, 5)
                next_retry_at = now + timedelta(seconds=backoff_base + backoff_jitter)
                await self.outbox_events_repo.mark_outbox_retry(
                    event=event, next_retry_at=next_retry_at, last_error=error_message, updated_at=now,
                )
                outbox_status = "retry_scheduled"

            if user_id > 0:
                await self.security_repo.add_security_event(
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

        except Exception:
            pass


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
