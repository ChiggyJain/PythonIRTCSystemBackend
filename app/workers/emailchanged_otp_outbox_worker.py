
"""
Worker: OUTBOX_EVENTS -> Kafka for EMAIL CHANGED OTP flow.
"""

import asyncio
from app.common.utils.logger import app_logger
from app.core.settings import get_settings
from app.domains.security.emailchanged_otp_outbox_dispatcher import EmailChangedOTPOutboxDispatcher
from app.domains.security.repository.sqlalchemy_repo import SecuritySQLAlchemyRepository
from app.infrastructure.database.session import AsyncSessionLocal
from app.infrastructure.kafka.client import build_producer


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
            try:
                async with AsyncSessionLocal() as db:
                    repo = SecuritySQLAlchemyRepository(db)
                    dispatcher = EmailChangedOTPOutboxDispatcher(repo=repo, producer=producer)
                    stats = await dispatcher.process_batch(batch_size=BATCH_SIZE)
                await asyncio.sleep(POLL_INTERVAL_IDLE_SECONDS if stats["processed"] == 0 else POLL_INTERVAL_ACTIVE_SECONDS)
            except Exception as exc:
                app_logger.error(f"emailchanged_otp_outbox_worker error: {exc}")
                await asyncio.sleep(2)
    finally:
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(run_worker())
