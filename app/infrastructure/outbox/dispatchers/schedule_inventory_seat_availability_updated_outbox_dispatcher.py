
import asyncio
import json
import signal
from app.common.utils.logger import app_logger
from app.core.settings import get_settings
from app.infrastructure.kafka.client import build_consumer
from app.infrastructure.elasticsearch.client import (
    build_elasticsearch_client
)
from app.infrastructure.elasticsearch.repositories.routes_repository import (
    RoutesElasticsearchRepository
)

settings = get_settings()
shutdown_event = asyncio.Event()

def shutdown_handler():
    app_logger.info(f"Shutdown signal received")
    shutdown_event.set()





async def update_schedule_inventory_to_elasticsearch(
    routes_repo: RoutesElasticsearchRepository,
    payload: dict
) -> bool:

    try:

        train_id = payload.get("train_id")
        schedule_id = payload.get("schedule_id")

        if not train_id:
            app_logger.error(
                "Invalid train_id"
            )
            return False

        if not schedule_id:
            app_logger.error(
                "Invalid schedule_id"
            )
            return False

        update_schedule_param = {
            "schedule_id": schedule_id,
            "available": payload.get("available", 0),
            "locked": payload.get("locked", 0),
            "booked": payload.get("booked", 0),
        }

        await routes_repo.upsert_schedule(
            train_id=str(train_id),
            schedules=update_schedule_param
        )

        return True

    except Exception as exc:
        app_logger.exception(
            f"Exception occurs to update schedule inventory into routes index document: {exc}"
        )
        return False


async def run_worker():

    consumer = build_consumer(
        topic=(
            settings
            .KAFKA_SCHEDULE_INVENTORY_SEAT_AVAILABILITY_UPDATED_TOPIC
        ),
        group_id=(
            settings
            .KAFKA_SCHEDULE_INVENTORY_SEAT_AVAILABILITY_UPDATED_TOPIC_CONSUMER_GROUP
        ),
        client_id=(
            f"{settings.KAFKA_CLIENT_ID}"
            "-schedule-inventory-consumer"
        ),
    )

    es_client_instances = build_elasticsearch_client()
    routes_repo = RoutesElasticsearchRepository(
        es_client_instances=es_client_instances,
        index_name=settings.ELASTICSEARCH_ROUTES_INDEX
    )
    await consumer.start()
    app_logger.info(
        "schedule inventory seat availability updated onsumer started"
    )

    try:

        while not shutdown_event.is_set():
            try:
                message_batch = await asyncio.wait_for(
                    consumer.getmany(timeout_ms=1000),
                    timeout=2
                )
                for tp, messages in message_batch.items():
                    for message in messages:
                        payload = json.loads(message.value.decode("utf-8"))
                        success = (
                            await update_schedule_inventory_to_elasticsearch(
                                routes_repo=routes_repo,
                                payload=payload
                            )
                        )
                        if success:
                            await consumer.commit()
                            app_logger.info(
                                f"Successfully updated schedule inventory into index routes document for schedule_id: {payload.get('schedule_id')}"
                            )
                        else:
                            app_logger.error(
                                f"Failed to update schedule inventory into index routes document for schedule_id: {payload.get('schedule_id')}"
                            )
            except asyncio.TimeoutError:
                continue    
            except Exception as exc:
                app_logger.exception(
                    f"Schedule inventory worker processing error: "
                    f"{exc}"
                )
                await asyncio.sleep(1)

    finally:
        app_logger.info(
            "Gracefully shutting down"
        )
        await consumer.stop()
        await es_client_instances.close()
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