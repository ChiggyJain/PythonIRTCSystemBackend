
import asyncio
import json
from app.common.utils.logger import app_logger
from app.core.settings import get_settings
from app.domains.security.consumers.emailverification_otp_dispatch_consumer import EmailVerificationOtpDispatchConsumerService
from app.infrastructure.kafka.client import build_consumer

settings = get_settings()


async def run_worker() -> None:
    consumer = build_consumer(
        topic=settings.EMAILVERIFICATION_OTP_DISPATCH_TOPIC,
        group_id=settings.EMAILVERIFICATION_OTP_DISPATCH_CONSUMER_GROUP,
        client_id=f"{settings.KAFKA_CLIENT_ID}-emailverification-consumer",
    )
    await consumer.start()
    app_logger.info("emailverification_otp_dispatch_consumer_worker started")
    try:
        async for message in consumer:
            try:
                payload = json.loads(message.value.decode("utf-8"))
                service = EmailVerificationOtpDispatchConsumerService()
                await service.process_payload(payload)
                await consumer.commit()
            except Exception as exc:
                app_logger.error(f"emailverification_otp_dispatch_consumer_worker error: {exc}")
                await asyncio.sleep(0.2)
    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(run_worker())
