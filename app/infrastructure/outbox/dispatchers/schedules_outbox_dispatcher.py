
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



async def add_schedules_to_elasticsearch(
    routes_repo: RoutesElasticsearchRepository,
    payload: dict
) -> bool:

    try:

        train_details = payload.get("train_details", {})
        train_id = train_details.get("train_id")

        if not train_id:
            app_logger.error(
                "train_id missing in payload"
            )
            return False

        update_schedule_param = {
            "schedule_id": payload.get("schedule_id"),
            "departure_date": payload.get("departure_date", ""),
            "total": train_details.get("total_seats", 0),
            "available": 0,
            "locked": 0,
            "booked": 0,
            "status": payload.get(
                "status", "A"
            )
        }

        await routes_repo.upsert_schedule(
            train_id=str(train_id),
            schedules=update_schedule_param
        )

        return True

    except Exception as exc:
        app_logger.exception(
            f"Exception occurs to add schedules into routes index document: {exc}"
        )
        return False


async def run_worker():

    consumer = build_consumer(
        topic=settings.KAFKA_SCHEDULE_TOPIC,
        group_id=(
            settings
            .KAFKA_SCHEDULE_TOPIC_CONSUMER_GROUP
        ),
        client_id=(
            f"{settings.KAFKA_CLIENT_ID}"
            "-schedules-consumer"
        ),
    )

    es_client_instances = build_elasticsearch_client()
    routes_repo = RoutesElasticsearchRepository(
        es_client_instances=es_client_instances,
        index_name=settings.ELASTICSEARCH_ROUTES_INDEX
    )
    await consumer.start()
    app_logger.info(
        "schedules_consumer_worker started"
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
                        if shutdown_event.is_set():
                            break
                        payload = json.loads(message.value.decode("utf-8"))
                        event_type = payload.get("event_type")
                        success = False
                        if event_type == "SCHEDULES_CREATE":
                            success = (
                                await add_schedules_to_elasticsearch(
                                    routes_repo=routes_repo,
                                    payload=payload
                                )
                            )
                        if event_type == "SCHEDULES_UPDATE":
                            pass    
                        if event_type == "SCHEDULES_DELETE":
                            pass
                        if success:
                            await consumer.commit()
                            app_logger.info(
                                f"Successfully scheudles into index routes document for event_type: {event_type}, schedule_id: {payload.get('schedule_id')}"
                            )
                        else:
                            app_logger.error(
                                f"Failed scheudles into index routes document for event_type: {event_type}, schedule_id: {payload.get('schedule_id')}"
                            )

            except asyncio.TimeoutError:
                continue    
            except Exception as exc:
                app_logger.exception(
                    f"Schedules worker processing error: {exc}"
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