
import asyncio
import json
import signal
from app.common.utils.logger import app_logger
from app.core.settings import get_settings
from app.infrastructure.kafka.client import build_consumer
from app.infrastructure.database.session import AsyncSessionLocal
from app.domains.inventory.services.inventory_services import (
    InventoryService,
)

settings = get_settings()
shutdown_event = asyncio.Event()

def shutdown_handler():
    app_logger.info(f"Shutdown signal received")
    shutdown_event.set()




async def initialize_schedule_inventory_process_details(payload: dict) -> bool:
    async with AsyncSessionLocal() as db:
        service = InventoryService(db_session=db)
        response = await service.process_train_schedule_created_event_for_inventory(payload=payload)
        result = json.loads(response.body)
        if result.get("status_code") == 201:
            return True
        return False


async def run_worker() -> None:
    consumer = build_consumer(
        topic=settings.KAFKA_SCHEDULE_TOPIC,
        group_id=settings.KAFKA_SCHEDULE_INVENTORY_CONSUMER_GROUP,
        client_id=f"{settings.KAFKA_CLIENT_ID}-schedules-inventory-consumer",
    )
    await consumer.start()
    app_logger.info("schedules_inventory_consumer_worker started")
    try:
        while not shutdown_event.is_set():
            try:
                message_batch = await asyncio.wait_for(
                    consumer.getmany(timeout_ms=1000),
                    timeout=2
                )
                for tp, messages in message_batch.items():
                    for message in messages:
                        if shutdown_event.is_set():
                            break
                    payload = json.loads(message.value.decode("utf-8"))
                    topic_name = message.topic
                    event_type = payload.get("event_type", "")
                    success = False
                    print(f"Topic: {topic_name}, Payload: {payload}")
                    if event_type == "SCHEDULES_CREATE":
                        success = await initialize_schedule_inventory_process_details(payload)    
                    if event_type == "SCHEDULES_UPDATE":
                        pass
                    if event_type == "SCHEDULES_DELETE":
                        pass
                    if success:
                        print(f"Successfully schedule inventory (CRUD) details for event_type: {event_type}, Schedule-ID: {payload.get("schedule_id", 0)}")
                        await consumer.commit()
                    else:
                        print(f"Failed schedule inventory (CRUD) details for event_type: {event_type}, Schedule-ID: {payload.get("schedule_id", 0)}")
            except asyncio.TimeoutError:
                continue    
            except Exception as exc:
                print(f"schedules_inventory_consumer_worker error: {exc}")
                await asyncio.sleep(0.2)
                
    finally:
        app_logger.info(
            "Gracefully shutting down"
        )
        await consumer.stop()
        app_logger.info(
            "Shutdown completed"
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
