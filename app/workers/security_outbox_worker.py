
"""
Outbox publisher worker:
OUTBOX_EVENTS -> Kafka topic
"""

import asyncio
from app.common.utils.logger import app_logger
from app.core.settings import get_settings
from app.domains.security.outbox_dispatcher import SecurityOutboxDispatcher
from app.domains.security.repository.sqlalchemy_repo import SecuritySQLAlchemyRepository
from app.infrastructure.database.session import AsyncSessionLocal
from app.infrastructure.kafka.client import build_producer


settings = get_settings()

POLL_INTERVAL_IDLE_SECONDS = 2
POLL_INTERVAL_ACTIVE_SECONDS = 0.2
BATCH_SIZE = 100


async def run_worker() -> None:
    producer = build_producer(
        client_id=f"{settings.KAFKA_CLIENT_ID}-outbox-publisher"
    )
    await producer.start()
    app_logger.info("pwdchanged_otp_outbox_worker started")

    try:
        while True:
            try:
                async with AsyncSessionLocal() as db:
                    repo = SecuritySQLAlchemyRepository(db)
                    dispatcher = SecurityOutboxDispatcher(
                        repo=repo,
                        producer=producer,
                    )
                    stats = await dispatcher.process_batch(
                        batch_size=BATCH_SIZE
                    )

                if stats["processed"] == 0:
                    await asyncio.sleep(POLL_INTERVAL_IDLE_SECONDS)
                else:
                    await asyncio.sleep(POLL_INTERVAL_ACTIVE_SECONDS)

            except Exception as exc:
                app_logger.error(f"pwdchanged_otp_outbox_worker error: {exc}")
                await asyncio.sleep(2)

    finally:
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(run_worker())
