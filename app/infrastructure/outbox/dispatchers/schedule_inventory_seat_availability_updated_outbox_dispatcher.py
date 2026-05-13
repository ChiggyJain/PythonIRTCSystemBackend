
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
        train_id = payload.get("train_id", 0)
        update_schedule_param = {
            "schedule_id" : payload.get("schedule_id", 0),
            "available" : payload.get("available", 0),
            "locked" : payload.get("locked", 0),
            "booked" : payload.get("booked", 0),
        }
        await routes_repo.upsert_schedule(train_id=train_id, schedules=update_schedule_param)
        await es_client.close()
        return True
    except Exception as e:
        print(f"ES indexing error: {e}")
        return False


async def run_worker() -> None:
    consumer = build_consumer(
        topic=settings.KAFKA_SCHEDULE_INVENTORY_SEAT_AVAILABILITY_UPDATED_TOPIC,
        group_id=settings.KAFKA_SCHEDULE_INVENTORY_SEAT_AVAILABILITY_UPDATED_TOPIC_CONSUMER_GROUP,
        client_id=f"{settings.KAFKA_CLIENT_ID}-schedules-inventory-seat-availability-updated-consumer",
    )
    await consumer.start()
    app_logger.info("schedules_inventory_seat_availability_updated_consumer_worker started")
    try:
        async for message in consumer:
            try:
                payload = json.loads(message.value.decode("utf-8"))
                topic_name = message.topic
                print(f"Topic: {topic_name}, Payload: {payload}")
                success = await index_to_elasticsearch(payload)
                if success:
                    print(f"Successfully updated schedule-inventory into index-route using Schedule-ID: {payload.get('schedule_id')}")
                else:
                    print(f"Failed to update schedule-inventory into index-route using Schedule-ID: {payload.get('schedule_id')}")
                await consumer.commit()                
            except Exception as exc:
                print(f"schedules_inventory_seat_availability_updated_consumer_worker error: {exc}")
                await asyncio.sleep(0.2)
    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(run_worker())
