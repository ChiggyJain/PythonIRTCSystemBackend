
import asyncio
import json
from app.common.utils.logger import app_logger
from app.core.settings import get_settings
from app.infrastructure.kafka.client import build_consumer
from app.infrastructure.elasticsearch.client import build_elasticsearch_client
from app.infrastructure.elasticsearch.repositories.routes_repository import RoutesElasticsearchRepository

settings = get_settings()


async def index_to_elasticsearch(payload: dict) -> bool:
    try:
        es_client = build_elasticsearch_client(settings.ELASTICSEARCH_ROUTES_INDEX)
        routes_repo = RoutesElasticsearchRepository(es_client)
        existing_es_documents = await routes_repo.get_by_id(train_id=payload.get("train_id"))
        print(f"existing_es_documents: {existing_es_documents}")
    except Exception as e:
        app_logger.error(f"ES indexing error: {e}")
        return False


async def run_worker() -> None:
    consumer = build_consumer(
        topic=settings.MASTERDATA_SCHEDULE_EVENT_TOPIC,
        group_id=settings.MASTERDATA_SCHEDULE_CONSUMER_GROUP,
        client_id=f"{settings.KAFKA_CLIENT_ID}-masterdata-schedules-consumer",
    )
    await consumer.start()
    app_logger.info("masterdata_schedules_dispatch_consumer_worker started")
    try:
        async for message in consumer:
            try:
                payload = json.loads(message.value.decode("utf-8"))
                app_logger.info(f"Received payload: {payload}")
                # Index to Elasticsearch
                success = await index_to_elasticsearch(payload)
                if success:
                    app_logger.info(f"Successfully indexed ScheduledID: {payload.get('schedule_id')}")
                else:
                    app_logger.error(f"Failed to index ScheduledID: {payload.get('schedule_id')}")
                # await consumer.commit()                
            except Exception as exc:
                app_logger.error(f"masterdata_schedules_dispatch_consumer_worker error: {exc}")
                await asyncio.sleep(0.2)
    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(run_worker())
