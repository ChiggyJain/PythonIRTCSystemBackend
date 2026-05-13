
import asyncio
import json
from app.common.utils.logger import app_logger
from app.infrastructure.database.session import AsyncSessionLocal
from app.core.settings import get_settings
from app.infrastructure.kafka.client import build_consumer
from app.domains.booking.services.booking_services import BookingService

settings = get_settings()

async def run_worker() -> None:
    consumer = build_consumer(
        topic=[
            settings.KAFKA_BOOKING_PAYMENT_SUCCESS_TOPIC,
            settings.KAFKA_BOOKING_PAYMENT_FAILED_TOPIC,
        ],
        group_id=settings.KAFKA_BOOKING_PAYMENT_SUCCESSFAILED_TOPIC_CONSUMER_GROUP,
        client_id=f"{settings.KAFKA_CLIENT_ID}-payment-orders-updated-status-consumer",
    )
    await consumer.start()
    app_logger.info("payment_orders_updated_status_consumer_worker started")
    try:
        async for message in consumer:
            try:
                payload = json.loads(message.value.decode("utf-8"))
                topic_name = message.topic
                async with AsyncSessionLocal() as db_session:
                    service = BookingService(db_session)
                    if (topic_name == settings.KAFKA_BOOKING_PAYMENT_SUCCESS_TOPIC):
                        rsp = await service.process_booking_payment_orders_success_details(payload=payload)
                    elif (topic_name == settings.KAFKA_BOOKING_PAYMENT_SUCCESS_TOPIC):
                        rsp = await service.process_booking_payment_orders_failed_details(payload=payload)
                    await consumer.commit()
            except Exception as exc:
                app_logger.error(f"payment_orders_updated_status_consumer_worker error: {exc}")
                await asyncio.sleep(0.2)
    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(run_worker())
