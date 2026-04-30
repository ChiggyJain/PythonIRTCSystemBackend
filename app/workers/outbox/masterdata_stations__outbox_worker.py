
import json
import asyncio
from app.infrastructure.database.session import AsyncSessionLocal
from app.common.utils.logger import app_logger
from app.core.settings import get_settings
from app.common.utils.datetime import now_ist
from app.infrastructure.kafka.client import build_producer
from app.infrastructure.outbox.repository.sqlalchemy_repo import OutboxEventsSQLAlchemyRepository
from app.infrastructure.outbox.retry_handlers.outbox_retryhandler_factory import OutboxRetryHandlerFactory


settings = get_settings()
POLL_INTERVAL_IDLE_SECONDS = 2
POLL_INTERVAL_ACTIVE_SECONDS = 0.2
BATCH_SIZE = 100


async def run_worker() -> None:

    producer = build_producer(client_id=f"{settings.KAFKA_CLIENT_ID}-emailchanged-outbox-publisher")
    await producer.start()
    app_logger.info("emailchanged_otp_outbox_worker started")

    try:

        while True:

            processed = False

            for loopNo in range(1, BATCH_SIZE):

                # STEP1: LOCK + MARK PROCESSING
                async with AsyncSessionLocal() as db:
                    async with db.begin():
                        # fetching outbox_event repository class object
                        outbox_repo = OutboxEventsSQLAlchemyRepository(db)
                        # fetching pending/retry/ outbox event details only
                        events = await outbox_repo.fetch_pending_outbox_events(
                            event_type="EMAILCHANGED_OTP_DISPATCH_REQUESTED_V1", limit=1, now_time=now_ist(),
                        )
                        if not events:
                            break
                        event = events[0]
                        payload = event.payload_json or {}
                        user_id = int(payload.get("user_id") or 0)
                        # updating outbox_events status as processing
                        updated_at = now_ist()
                        await outbox_repo.mark_outbox_processing(event=event, updated_at=updated_at)
                
                # STEP2: Kafka (OUTSIDE transaction)
                try:
                    
                    # kafka topic
                    topic = settings.EMAILCHANGED_OTP_DISPATCH_TOPIC
                    # preparing message for publishing to the kafka topic
                    message = json.dumps(
                        {"outbox_id": event.id, "event_type": event.event_type, **payload},
                        separators=(",", ":"),
                    ).encode("utf-8")

                    # preparing key to used for publishing to the topic partition
                    key = str(user_id if user_id > 0 else 0).encode("utf-8")

                    # publish message to kafka topic
                    md = await producer.send_and_wait(topic=topic, key=key, value=message,)

                    # STEP 3: FINAL SUCCESS UPDATE
                    async with AsyncSessionLocal() as db:
                        async with db.begin():
                            outbox_repo = OutboxEventsSQLAlchemyRepository(db)
                            security_repo = SecuritySQLAlchemyRepository(db)
                            # fetching outbox event by given ID
                            event = await outbox_repo.get_by_id(event.id)
                            # updating outbox event status as published
                            published_at = now_ist()
                            await outbox_repo.mark_outbox_published(event=event, published_at=published_at)
                            # adding logs into security_event
                            await security_repo.add_security_event(
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
                 
                except Exception as exc:
                    # STEP4: RETRY / FAIL
                    async with AsyncSessionLocal() as db:
                        async with db.begin():
                            outbox_repo = OutboxEventsSQLAlchemyRepository(db)
                            security_repo = SecuritySQLAlchemyRepository(db)
                            event = await outbox_repo.get_by_id(event.id)
                            if event!=None:
                                params = {
                                    "retry_handler_type": "EMAILCHANGED_OTP", "outbox_repo": outbox_repo, "security_repo": security_repo
                                }
                                emailchanged_otp_outbox_retry_handler_class_obj = OutboxRetryHandlerFactory.getOutboxRetryHandler(**params)
                                params = {
                                    "event": event, "user_id": user_id, "error_message": str(exc)
                                }
                                await emailchanged_otp_outbox_retry_handler_class_obj.handle(**params)


                processed = True

            await asyncio.sleep(POLL_INTERVAL_ACTIVE_SECONDS if processed else POLL_INTERVAL_IDLE_SECONDS)

    finally:
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(run_worker())
