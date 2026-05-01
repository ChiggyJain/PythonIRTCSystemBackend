
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

    producer = build_producer(client_id=f"{settings.KAFKA_CLIENT_ID}-masterdata-schedules-outbox-publisher")
    await producer.start()
    app_logger.info("masterdata_schedules_outbox_worker started")

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
                            aggregate_type="ROUTES", limit=1, now_time=now_ist(),
                        )
                        if not events:
                            break
                        event = events[0]
                        payload = event.payload_json or {}
                        # updating outbox_events status as processing
                        updated_at = now_ist()
                        await outbox_repo.mark_outbox_processing(event=event, updated_at=updated_at)
                
                # STEP2: Kafka (OUTSIDE transaction)
                try:
                    
                    # kafka topic
                    topic = settings.MASTERDATA_ROUTE_EVENT_TOPIC
                    # preparing message for publishing to the kafka topic
                    message = json.dumps(
                        {"outbox_id": event.id, "event_type": event.event_type, **payload},
                        separators=(",", ":"),
                    ).encode("utf-8")

                    # preparing key to used for publishing to the topic partition
                    key = str(payload.get("route_id", 0)).encode("utf-8")

                    # publish message to kafka topic
                    md = await producer.send_and_wait(topic=topic, key=key, value=message,)

                    # STEP 3: FINAL SUCCESS UPDATE
                    async with AsyncSessionLocal() as db:
                        async with db.begin():
                            outbox_repo = OutboxEventsSQLAlchemyRepository(db)
                            # fetching outbox event by given ID
                            event = await outbox_repo.get_by_id(event.id)
                            # updating outbox event status as published
                            published_at = now_ist()
                            await outbox_repo.mark_outbox_published(event=event, published_at=published_at)
                 
                except Exception as exc:
                    # STEP4: RETRY / FAIL
                    async with AsyncSessionLocal() as db:
                        async with db.begin():
                            outbox_repo = OutboxEventsSQLAlchemyRepository(db)
                            event = await outbox_repo.get_by_id(event.id)
                            if event!=None:
                                params = {
                                    "retry_handler_type": "MASTERDATA_ROUTES", "outbox_repo": outbox_repo
                                }
                                masterdata_routes_outbox_retry_handler_class_obj = OutboxRetryHandlerFactory.getOutboxRetryHandler(**params)
                                params = {
                                    "event": event, "error_message": str(exc)
                                }
                                await masterdata_routes_outbox_retry_handler_class_obj.handle(**params)


                processed = True

            await asyncio.sleep(POLL_INTERVAL_ACTIVE_SECONDS if processed else POLL_INTERVAL_IDLE_SECONDS)

    finally:
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(run_worker())
