
import asyncio
import json
import signal
from app.common.utils.logger import app_logger
from app.core.settings import get_settings
from app.infrastructure.kafka.client import build_consumer
from app.infrastructure.elasticsearch.client import build_elasticsearch_client
from app.infrastructure.elasticsearch.repositories.station_repository import (
    StationElasticsearchRepository
)

settings = get_settings()
shutdown_event = asyncio.Event()

def shutdown_handler():
    app_logger.info(f"Shutdown signal received")
    shutdown_event.set()



async def add_station_to_elasticsearch(
    station_repo: StationElasticsearchRepository,
    payload: dict
) -> bool:
    
    try:

        es_document = {
            "station_id": payload.get("station_id", 0),
            "name": payload.get("name", ""),
            "code": payload.get("code", ""),
            "city": payload.get("city", ""),
            "state": payload.get("state", ""),
            "suggest": {
                "input": [
                    value for value in [
                        payload.get("name", ""),
                        payload.get("code", ""),
                        payload.get("city", "")
                    ] if value
                ],
                "weight": 10
            }
        }
        await station_repo.index_document(
            doc_id=str(payload.get("station_id")),
            document=es_document
        )
        return True

    except Exception as exc:
        app_logger.exception(
            f"Exception occurs to add station index document: {exc}"
        )
        return False


async def run_worker() -> None:

    consumer = build_consumer(
        topic=settings.KAFKA_STATION_TOPIC,
        group_id=settings.KAFKA_STATION_TOPIC_CONSUMER_GROUP,
        client_id=f"{settings.KAFKA_CLIENT_ID}-stations-consumer",
    )
    es_client_instances = build_elasticsearch_client()
    station_repo = StationElasticsearchRepository(
        es_client_instances=es_client_instances,
        index_name=settings.ELASTICSEARCH_STATIONS_INDEX
    )
    await station_repo.create_index_if_not_exists()
    await consumer.start()
    app_logger.info("stations_consumer_worker started")

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
                        if event_type == "STATIONS_CREATE":
                            success = await add_station_to_elasticsearch(
                                station_repo=station_repo,
                                payload=payload
                            )
                        elif event_type == "STATIONS_UPDATE":
                            pass
                        elif event_type == "STATIONS_DELETE":
                            pass
                        if success:
                            await consumer.commit()
                            app_logger.info(
                                f"Successfully index station document for event_type: {event_type}, station_id: {payload.get('station_id')}"
                            )
                        else:
                            app_logger.error(
                                f"Failed index station document for event_type: {event_type}, station_id: {payload.get('station_id')}"
                            )

            except asyncio.TimeoutError:
                continue
            except Exception as exc:
                app_logger.exception(
                    f"Stations worker processing error: {exc}"
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