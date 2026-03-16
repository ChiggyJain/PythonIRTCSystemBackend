"""
OTP dispatch consumer worker:
Kafka topic -> provider send
"""

import asyncio
import json
from app.common.utils.logger import app_logger
from app.core.settings import get_settings
from app.domains.security.otp_dispatch_consumer import OtpDispatchConsumerService
from app.domains.security.repository.sqlalchemy_repo import SecuritySQLAlchemyRepository
from app.infrastructure.database.session import AsyncSessionLocal
from app.infrastructure.kafka.client import build_consumer
from app.infrastructure.otp.provider_factory import (
    get_email_otp_sender,
    get_sms_otp_sender,
)


settings = get_settings()


async def run_worker() -> None:
    consumer = build_consumer(
        topic=settings.OTP_DISPATCH_TOPIC,
        group_id=settings.OTP_DISPATCH_CONSUMER_GROUP,
        client_id=f"{settings.KAFKA_CLIENT_ID}-otp-consumer",
    )
    await consumer.start()
    app_logger.info("otp_dispatch_consumer_worker started")

    email_sender = get_email_otp_sender()
    sms_sender = get_sms_otp_sender()

    try:
        async for message in consumer:
            try:
                payload = json.loads(message.value.decode("utf-8"))

                async with AsyncSessionLocal() as db:
                    repo = SecuritySQLAlchemyRepository(db)
                    service = OtpDispatchConsumerService(
                        repo=repo,
                        email_sender=email_sender,
                        sms_sender=sms_sender,
                    )
                    await service.process_payload(payload)

            except Exception as exc:
                app_logger.error(f"otp_dispatch_consumer_worker message error: {exc}")

            finally:
                # Commit offset after handling to avoid poison-message loops.
                await consumer.commit()

    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(run_worker())
