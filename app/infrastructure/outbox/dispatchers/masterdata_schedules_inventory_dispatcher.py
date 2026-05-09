
import asyncio
import json
from app.common.utils.logger import app_logger
from app.core.settings import get_settings
from app.infrastructure.kafka.client import build_consumer
from app.infrastructure.database.session import AsyncSessionLocal
from app.domains.inventory.services.inventory_services import (
    InventoryService,
)

settings = get_settings()


async def process_message(payload: dict) -> bool:
    async with AsyncSessionLocal() as db:
        service = InventoryService(db_session=db)
        result = await service.process_train_schedule_created_event_for_inventory(payload=payload)
        app_logger.info(
            f"inventory_schedule_consumer | schedule_id={payload.get('schedule_id')} | status_code={result.get('status_code')}"
        )
        return True


async def run_worker() -> None:
    consumer = build_consumer(
        topic=settings.MASTERDATA_SCHEDULE_CREATED,
        group_id=settings.MASTERDATA_SCHEDULE_INVENTORY_CONSUMER_GROUP,
        client_id=f"{settings.KAFKA_CLIENT_ID}-masterdata-schedules-inventory-consumer",
    )
    await consumer.start()
    app_logger.info("masterdata_schedules_inventory_dispatch_consumer_worker started")
    try:
        async for message in consumer:
            try:
                payload = json.loads(message.value.decode("utf-8"))
                app_logger.info(f"inventory_consumer received payload: {payload}")
                success = await process_message(payload)
                if success:
                    await consumer.commit()
            except Exception as exc:
                app_logger.error(f"masterdata_schedules_inventory_dispatch_consumer_worker error: {exc}")
                await asyncio.sleep(0.2)
    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(run_worker())
