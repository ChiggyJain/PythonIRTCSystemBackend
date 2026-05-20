
import json
import asyncio
import signal
from app.infrastructure.database.session import AsyncSessionLocal
from app.common.utils.logger import app_logger
from app.core.settings import get_settings
from app.common.utils.datetime import now_ist
from app.infrastructure.kafka.client import build_producer
from app.infrastructure.outbox.repository.sqlalchemy_repo import OutboxEventsSQLAlchemyRepository
from app.infrastructure.outbox.retry_handlers.outbox_retryhandler_factory import OutboxRetryHandlerFactory


settings = get_settings()
shutdown_event = asyncio.Event()

POLL_INTERVAL_IDLE_SECONDS = 2
POLL_INTERVAL_ACTIVE_SECONDS = 1
BATCH_SIZE = 100

def shutdown_handler():
    app_logger.info(
        "Shutdown signal received"
    )
    shutdown_event.set()



async def process_event(
    producer,
    event
):

    payload = event.payload_json or {}
    topic = settings.KAFKA_EMAILCHANGED_OTP_TOPIC
    
    message = json.dumps(
        {
            "outbox_id": event.id,
            "event_type": event.event_type,
            **payload
        },
        separators=(",", ":"),
    ).encode("utf-8")

    key = str(
        payload.get("user_id", 0)
    ).encode("utf-8")

    await producer.send_and_wait(
        topic=topic,
        key=key,
        value=message
    )



async def run_worker() -> None:

    producer = build_producer(
        client_id=f"{settings.KAFKA_CLIENT_ID}-emailchanged-outbox-publisher"
    )
    await producer.start()
    app_logger.info("emailchanged_otp_outbox_worker started")

    try:

        while not shutdown_event.is_set():

            processed = False

            # Step1: Fetching queries in batches for LOCK + MARK PROCESSING
            async with AsyncSessionLocal() as db:
                async with db.begin():
                    outbox_repo = OutboxEventsSQLAlchemyRepository(db)
                    events = await outbox_repo.fetch_pending_outbox_events(
                        aggregate_type="OTP_CHALLENGE", 
                        event_type="EMAILCHANGED_OTP_REQUESTED",
                        limit=BATCH_SIZE, 
                        now_time=now_ist(),
                    )
                    if events:
                        event_ids = [event.id for event in events]
                        updated_at = now_ist()
                        await outbox_repo.bulk_mark_processing(
                            event_ids=event_ids,
                            updated_at=updated_at
                        )
            
            if not events:
                await asyncio.sleep(
                    POLL_INTERVAL_IDLE_SECONDS
                )
                continue
        
            # Step2: Processing events outside db transactions
            for event in events:

                if shutdown_event.is_set():
                    app_logger.info(
                        "Shutdown detected. "
                        "Stopping new processing."
                    )
                    break

                try:

                    await process_event(
                        producer=producer,
                        event=event
                    )

                    # Step3: Mark published
                    async with AsyncSessionLocal() as db:
                        async with db.begin():
                            outbox_repo = OutboxEventsSQLAlchemyRepository(db)
                            db_event = await outbox_repo.get_by_id(event.id)
                            if db_event:
                                await outbox_repo.mark_outbox_published(
                                    event=db_event,
                                    published_at=now_ist()
                                )
                    
                    processed = True
                    app_logger.info(
                        f"Published outbox_id="
                        f"{event.id}"
                    )
                
                except asyncio.CancelledError:
                    app_logger.warning(
                        "Worker cancelled"
                    )
                    raise

                except Exception as exc:
                    
                    app_logger.exception(
                        f"Failed publishing "
                        f"outbox_id={event.id}, "
                        f"error={exc}"
                    )

                    # Step4: Retry/Fail
                    async with AsyncSessionLocal() as db:
                        async with db.begin():
                            outbox_repo = OutboxEventsSQLAlchemyRepository(db)
                            db_event = await outbox_repo.get_by_id(event.id)
                            if db_event:
                                retry_handler = OutboxRetryHandlerFactory.getOutboxRetryHandler(
                                    retry_handler_type="EMAILCHANGED_OTP",
                                    outbox_repo=outbox_repo
                                )
                                await retry_handler.handle(
                                    event=db_event,
                                    error_message=str(exc)
                                )

                
                await asyncio.sleep(
                    POLL_INTERVAL_ACTIVE_SECONDS
                    if processed
                    else POLL_INTERVAL_IDLE_SECONDS
                )

    finally:
        app_logger.info(
            "Flushing Kafka producer"
        )
        await producer.flush()
        app_logger.info(
            "Stopping Kafka producer"
        )
        await producer.stop()
        app_logger.info(
            "Outbox worker shutdown completed"
        )


async def main():
    loop = asyncio.get_running_loop()
    loop.add_signal_handler(
        signal.SIGINT,
        shutdown_handler
    )
    loop.add_signal_handler(
        signal.SIGTERM,
        shutdown_handler
    )
    await run_worker()


if __name__ == "__main__":
    asyncio.run(main())