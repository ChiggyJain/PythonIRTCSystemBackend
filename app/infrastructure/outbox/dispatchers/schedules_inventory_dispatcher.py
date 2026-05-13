
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
        response = await service.process_train_schedule_created_event_for_inventory(payload=payload)
        result = json.loads(response.body)
        return True


async def run_worker() -> None:
    consumer = build_consumer(
        topic=settings.KAFKA_SCHEDULE_CREATED_TOPIC,
        group_id=settings.KAFKA_SCHEDULE_INVENTORY_CONSUMER_GROUP,
        client_id=f"{settings.KAFKA_CLIENT_ID}-schedules-inventory-consumer",
    )
    await consumer.start()
    app_logger.info("schedules_inventory_consumer_worker started")
    try:
        async for message in consumer:
            try:
                payload = json.loads(message.value.decode("utf-8"))
                topic_name = message.topic
                print(f"Topic: {topic_name}, Payload: {payload}")
                success = await process_message(payload)
                if success:
                    print(f"Successfully initialize inventory details using Schedule-ID: {payload.get("schedule_id", 0)}")
                else:
                    print(f"Fail to initialize inventory details using Schedule-ID: {payload.get("schedule_id", 0)}")
                await consumer.commit()
            except Exception as exc:
                print(f"schedules_inventory_consumer_worker error: {exc}")
                await asyncio.sleep(0.2)
    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(run_worker())
