
import asyncio
import json
from app.common.utils.logger import app_logger
from app.core.settings import get_settings
from app.infrastructure.kafka.client import build_consumer

settings = get_settings()

async def run_worker() -> None:
    consumer = build_consumer(
        topic=settings.KAFKA_BOOKING_STATUS_TOPIC,
        group_id=settings.KAFKA_BOOKING_STATUS_EMAIL_CONSUMER_GROUP,
        client_id=f"{settings.KAFKA_CLIENT_ID}-booking-status-send-email-otp-consumer",
    )
    await consumer.start()
    app_logger.info("booking_status_send_email_consumer started")
    try:
        async for message in consumer:
            try:
                payload = json.loads(message.value.decode("utf-8"))
                topic_name = message.topic
                print(f"Topic: {topic_name}, Payload: {payload}")
                await consumer.commit()
            except Exception as exc:
                print(f"booking_status_send_email_consumer error: {exc}")
                await asyncio.sleep(0.2)
    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(run_worker())
