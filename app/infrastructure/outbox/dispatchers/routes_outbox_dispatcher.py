
import asyncio
import json
import signal
from app.common.utils.logger import app_logger
from app.core.settings import get_settings
from app.infrastructure.kafka.client import build_consumer
from app.infrastructure.elasticsearch.client import build_elasticsearch_client
from app.infrastructure.elasticsearch.repositories.routes_repository import (
    RoutesElasticsearchRepository
)

settings = get_settings()
shutdown_event = asyncio.Event()

def shutdown_handler():
    app_logger.info(f"Shutdown signal received")
    shutdown_event.set()




def build_seat_summary(seat_details: list) -> dict:

    seat_summary = {
        "total": 0,
        "LOWER": 0,
        "MIDDLE": 0,
        "UPPER": 0,
        "SIDE_UPPER": 0,
        "SIDE_LOWER": 0
    }
    for seat in seat_details:
        seat_type = seat.get("seat_type")
        seat_summary["total"]+= 1
        if seat_type in seat_summary:
            seat_summary[seat_type]+= 1
    return seat_summary


async def add_routes_to_elasticsearch(
    routes_repo: RoutesElasticsearchRepository,
    payload: dict
) -> bool:

    try:

        train_details = payload.get("train_details", {})
        train_id = train_details.get("train_id", None)

        if not train_id:
            app_logger.error(
                "train_id missing in payload"
            )
            return False

        seat_summary = build_seat_summary(
            payload.get("seat_details", [])
        )
        existing_doc = await routes_repo.get_document(
            doc_id=str(train_id)
        )
        existing_schedules = []
        if existing_doc and existing_doc.get("_source"):
            existing_schedules = (
                existing_doc["_source"]
                .get("schedules", [])
            )
        es_document = {
            "train_id": train_id,
            "train_name": train_details.get(
                "train_name", ""
            ),
            "train_number": train_details.get(
                "train_number", ""
            ),
            "seatSummary": seat_summary,
            "routes": [
                {
                    "route_id": payload.get("route_id"),
                    "station_id": route.get(
                        "station_id"
                    ),
                    "name": route.get("name"),
                    "code": route.get("code"),
                    "city": route.get("city"),
                    "state": route.get("state"),
                    "sequence_number": route.get("sequence_number"),
                    "arrival_time": route.get("arrival_time"),
                    "departure_time": route.get("departure_time"),
                    "distance_from_origin": float(route.get("distance_from_origin", 0)),
                    "status": route.get("status")
                }
                for route in payload.get("station_details", [])
            ],
            "schedules": existing_schedules
        }

        await routes_repo.index_document(
            doc_id=str(train_id),
            document=es_document
        )

        return True

    except Exception as exc:
        app_logger.exception(
            f"Exception occurs to add routes index document: {exc}"
        )

        return False


async def run_worker():

    consumer = build_consumer(
        topic=settings.KAFKA_ROUTE_TOPIC,
        group_id=settings.KAFKA_ROUTE_TOPIC_CONSUMER_GROUP,
        client_id=(
            f"{settings.KAFKA_CLIENT_ID}"
            "-routes-consumer"
        ),
    )
    es_client_instances = build_elasticsearch_client()
    routes_repo = RoutesElasticsearchRepository(
        es_client_instances=es_client_instances,
        index_name=settings.ELASTICSEARCH_ROUTES_INDEX
    )
    await routes_repo.create_index_if_not_exists()
    await consumer.start()

    app_logger.info(
        "routes_consumer_worker started"
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
                        event_type = payload.get("event_type", "")
                        success = False
                        if event_type == "ROUTES_CREATE":
                            success = (
                                await add_routes_to_elasticsearch(
                                    routes_repo=routes_repo,
                                    payload=payload
                                )
                            )
                        if success:
                            await consumer.commit()
                            app_logger.info(
                                f"Successfully index routes document for event_type: {event_type}, route_id: {payload.get('route_id')}"
                            )
                        else:
                            app_logger.error(
                                f"Failed index routes document for event_type: {event_type}, route_id: {payload.get('route_id')}"
                            )

            except asyncio.TimeoutError:
                continue
            except Exception as exc:
                app_logger.exception(
                    f"Routes worker processing error: {exc}"
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