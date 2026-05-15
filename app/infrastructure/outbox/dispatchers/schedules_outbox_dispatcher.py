
import asyncio
import json
from app.common.utils.logger import app_logger
from app.core.settings import get_settings
from app.infrastructure.kafka.client import build_consumer
from app.infrastructure.elasticsearch.client import build_elasticsearch_client
from app.infrastructure.elasticsearch.repositories.routes_repository import RoutesElasticsearchRepository

settings = get_settings()


async def add_schedules_to_elasticsearch(payload: dict) -> bool:
    try:
        es_client_instances = build_elasticsearch_client()
        routes_repo = RoutesElasticsearchRepository(
            es_client_instances=es_client_instances,
            index_name=settings.ELASTICSEARCH_ROUTES_INDEX
        )
        train_id = payload.get("train_details", {}).get("train_id", 0)
        update_schedule_param = {
            "schedule_id" : payload.get("schedule_id", 0),
            "departure_date" : payload.get("departure_date", ""),
            "total" : payload.get("train_details", {}).get("total_seats", 0),
            "available" : 0,
            "locked" : 0,
            "booked" : 0,
            "status" : payload.get("status", "A"),
        }
        await routes_repo.upsert_schedule(
            train_id=str(train_id), 
            schedules=update_schedule_param
        )
        await es_client_instances.close()
        return True
    except Exception as e:
        app_logger.error(f"ES indexing error: {e}")
        return False


async def run_worker() -> None:
    consumer = build_consumer(
        topic=settings.KAFKA_SCHEDULE_TOPIC,
        group_id=settings.KAFKA_SCHEDULE_TOPIC_CONSUMER_GROUP,
        client_id=f"{settings.KAFKA_CLIENT_ID}-schedules-consumer",
    )
    await consumer.start()
    app_logger.info("schedules_consumer_worker started")
    try:
        async for message in consumer:
            try:
                payload = json.loads(message.value.decode("utf-8"))
                topic_name = message.topic
                event_type = payload.get("event_type", "")
                success = False
                print(f"Topic: {topic_name}, Payload: {payload}")
                if event_type == "SCHEDULES_CREATE":
                    success = await add_schedules_to_elasticsearch(payload)
                    if success:
                        print(f"Successfully added schedule into index-route of Scheduled-ID: {payload.get('schedule_id')}")
                    else:
                        print(f"Failed to add schedule into index-route of Scheduled-ID: {payload.get('schedule_id')}")
                if event_type == "SCHEDULES_UPDATE":
                    pass
                if event_type == "SCHEDULES_DELETE":
                    pass
                await consumer.commit()                
            except Exception as exc:
                print(f"schedules_consumer_worker error: {exc}")
                await asyncio.sleep(0.2)
    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(run_worker())
