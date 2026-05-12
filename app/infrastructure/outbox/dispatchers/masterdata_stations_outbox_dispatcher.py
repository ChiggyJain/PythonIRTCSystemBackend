
import asyncio
import json
from app.common.utils.logger import app_logger
from app.core.settings import get_settings
from app.infrastructure.kafka.client import build_consumer
from app.infrastructure.elasticsearch.client import build_elasticsearch_client
from app.infrastructure.elasticsearch.repositories.station_repository import StationElasticsearchRepository

settings = get_settings()


async def index_to_elasticsearch(payload: dict) -> bool:
    try:
        es_client = build_elasticsearch_client(settings.ELASTICSEARCH_STATIONS_INDEX)
        station_repo = StationElasticsearchRepository(es_client)
        # Create index with mapping if not exists
        await station_repo.create_index_if_not_exists()
        # Prepare ES document (only required fields)
        es_document = {
            "station_id": payload.get("station_id", 0),
            "name": payload.get("name", ""),
            "code": payload.get("code", ""),
            "city": payload.get("city", ""),
            "state": payload.get("state", ""),
            "suggest": {
                "input": [
                    v for v in [
                        payload.get("name", ""),
                        payload.get("code", ""),
                        payload.get("city", "")
                    ] if v
                ],
                "weight": 10
            }
        }
        # Index/upsert the document
        await station_repo.index(es_document)
        app_logger.info(f"Indexed station to ES using StationID: {payload.get('station_id')}")
        await es_client.close()
        return True
    except Exception as e:
        app_logger.error(f"ES indexing error: {e}")
        return False


async def run_worker() -> None:
    consumer = build_consumer(
        topic=settings.MASTERDATA_STATION_CREATED,
        group_id=settings.KAFKA_STATION_CONSUMER_GROUP,
        client_id=f"{settings.KAFKA_CLIENT_ID}-masterdata-stations-consumer",
    )
    await consumer.start()
    app_logger.info("masterdata_stations_dispatch_consumer_worker started")
    try:
        async for message in consumer:
            try:
                payload = json.loads(message.value.decode("utf-8"))
                app_logger.info(f"Received payload: {payload}")
                # Index to Elasticsearch
                success = await index_to_elasticsearch(payload)
                if success:
                    app_logger.info(f"Successfully indexed StationID: {payload.get('station_id')}")
                else:
                    app_logger.error(f"Failed to index StationID: {payload.get('station_id')}")
                await consumer.commit()                
            except Exception as exc:
                app_logger.error(f"masterdata_stations_dispatch_consumer_worker error: {exc}")
                await asyncio.sleep(0.2)
    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(run_worker())
