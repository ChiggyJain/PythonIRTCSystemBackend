
import asyncio
import json
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
        "schedule inventory consumer started"
    )

    try:

        async for message in consumer:

            try:

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

            except Exception as exc:
                app_logger.exception(
                    f"Schedule inventory worker processing error: "
                    f"{exc}"
                )
                await asyncio.sleep(1)

    finally:
        app_logger.info(
            "Close schedule inventory consumer and elasticsearch client"
        )
        await consumer.stop()
        await es_client_instances.close()


if __name__ == "__main__":

    asyncio.run(run_worker())