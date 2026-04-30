
"""
Worker: consume email-verification OTP topic and send email.
"""

import asyncio
import json
from app.common.utils.logger import app_logger
from app.core.settings import get_settings
from app.domains.security.emailverification_otp_dispatch_consumer_copy import (
    EmailVerificationOtpDispatchConsumerService,
)
from app.domains.security.repository.sqlalchemy_repo import SecuritySQLAlchemyRepository
from app.infrastructure.database.session import AsyncSessionLocal
from app.infrastructure.kafka.client import build_consumer
from app.infrastructure.otp.provider_factory import get_emailverification_email_otp_sender


settings = get_settings()


async def run_worker() -> None:
    consumer = build_consumer(
        topic=settings.EMAILVERIFICATION_OTP_DISPATCH_TOPIC,
        group_id=settings.EMAILVERIFICATION_OTP_DISPATCH_CONSUMER_GROUP,
        client_id=f"{settings.KAFKA_CLIENT_ID}-emailverification-consumer",
    )
    await consumer.start()
    app_logger.info("emailverification_otp_dispatch_consumer_worker started")
    email_sender = get_emailverification_email_otp_sender()
    try:
        async for message in consumer:
            try:
                payload = json.loads(message.value.decode("utf-8"))
                async with AsyncSessionLocal() as db:
                    repo = SecuritySQLAlchemyRepository(db)
                    service = EmailVerificationOtpDispatchConsumerService(
                        repo=repo,
                        email_sender=email_sender,
                    )
                    await service.process_payload(payload)
                # Commit only after successful processing.
                await consumer.commit()
            except Exception as exc:
                app_logger.error(f"emailverification_otp_dispatch_consumer_worker error: {exc}")
                # Do NOT commit on failure; message will be retried.
                await asyncio.sleep(0.2)            
    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(run_worker())
