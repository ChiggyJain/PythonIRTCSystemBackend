
import asyncio
import json
from app.common.utils.logger import app_logger
from app.core.settings import get_settings
from app.infrastructure.kafka.client import build_consumer
from app.infrastructure.elasticsearch.client import build_elasticsearch_client
from app.infrastructure.elasticsearch.repositories.station_repository import (
    StationElasticsearchRepository
)

settings = get_settings()


async def add_station(
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
        es_client_instances_instances=es_client_instances,
        index_name=settings.ELASTICSEARCH_STATIONS_INDEX
    )
    await station_repo.create_index_if_not_exists()
    await consumer.start()
    app_logger.info("stations_consumer_worker started")

    try:

        async for message in consumer:
            try:

                payload = json.loads(message.value.decode("utf-8"))
                event_type = payload.get("event_type")
                success = False

                if event_type == "STATIONS_CREATE":
                    success = await add_station(
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
                        f"Offset committed for "
                        f"station_id={payload.get('station_id')}"
                    )
                else:
                    app_logger.error(
                        f"Failed to add station index document station_id:{payload.get('station_id')}"
                    )

            except Exception as exc:
                app_logger.exception(
                    f"Stations Worker processing error: {exc}"
                )
                await asyncio.sleep(1)

    finally:
        app_logger.info(
            "Close stations consumer and elasticsearch client"
        )
        await consumer.stop()
        await es_client_instances.close()


if __name__ == "__main__":
    asyncio.run(run_worker())