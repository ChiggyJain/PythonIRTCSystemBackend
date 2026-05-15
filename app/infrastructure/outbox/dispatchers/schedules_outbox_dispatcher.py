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


async def add_schedules_to_elasticsearch(
    routes_repo: RoutesElasticsearchRepository,
    payload: dict
) -> bool:

    try:

        train_details = payload.get(
            "train_details", {}
        )

        train_id = train_details.get(
            "train_id"
        )

        if not train_id:

            app_logger.error(
                "train_id missing in payload"
            )

            return False

        update_schedule_param = {
            "schedule_id": payload.get(
                "schedule_id"
            ),
            "departure_date": payload.get(
                "departure_date", ""
            ),
            "total": train_details.get(
                "total_seats", 0
            ),
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
            f"Schedule indexing failed: {exc}"
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

    es_client = build_elasticsearch_client()

    routes_repo = RoutesElasticsearchRepository(
        es_client_instances=es_client,
        index_name=settings.ELASTICSEARCH_ROUTES_INDEX
    )

    await consumer.start()

    app_logger.info(
        "schedules_consumer_worker started"
    )

    try:

        async for message in consumer:

            try:

                payload = json.loads(
                    message.value.decode("utf-8")
                )

                event_type = payload.get(
                    "event_type"
                )

                success = False

                if event_type == "SCHEDULES_CREATE":

                    success = (
                        await add_schedules_to_elasticsearch(
                            routes_repo=routes_repo,
                            payload=payload
                        )
                    )

                if success:

                    await consumer.commit()

                    app_logger.info(
                        f"Committed offset "
                        f"schedule_id="
                        f"{payload.get('schedule_id')}"
                    )

                else:

                    app_logger.error(
                        f"Failed processing "
                        f"schedule_id="
                        f"{payload.get('schedule_id')}"
                    )

            except Exception as exc:

                app_logger.exception(
                    f"Worker error: {exc}"
                )

                await asyncio.sleep(1)

    finally:

        await consumer.stop()

        await es_client.close()


if __name__ == "__main__":

    asyncio.run(run_worker())