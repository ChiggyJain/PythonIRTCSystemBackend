
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
        # Create index with mapping if not exists
        await routes_repo.create_index_if_not_exists()
        # Prepare ES document (only required fields)
        route_id = payload.get('route_id', 0)
        train_details = payload.get("train_details")
        seatSummary = {
            "total" : 0, "LOWER" : 0, "MIDDLE" : 0, "UPPER" : 0, 
            "SIDE_UPPER" : 0, "SIDE_LOWER" : 0
        }
        for eachSeatObj in payload.get("seat_details"):
            seatSummary["total"]+= 1
            if eachSeatObj['seat_type'] in seatSummary:
                seatSummary[eachSeatObj['seat_type']]+= 1
        existing_doc = await routes_repo.get_by_id(train_details.get("train_id", 0))
        existing_schedules = []
        if existing_doc and existing_doc.get("_source"):
            existing_schedules = existing_doc["_source"].get("schedules", [])
        es_document = {
            "train_id": train_details.get("train_id", 0),
            "train_name": train_details.get("train_name", ""),
            "train_number": train_details.get("train_number", ""),
            "seatSummary" : seatSummary,
            "routes" : [
                {
                    "route_id" : route_id,
                    "station_id": rs['station_id'],
                    "name": rs['name'],
                    "code": rs['code'],
                    "city": rs['city'],
                    "state": rs['state'],
                    "sequence_number": rs['sequence_number'],
                    "arrival_time": rs['arrival_time'],
                    "departure_time": rs['departure_time'],
                    "distance_from_origin": float(rs['distance_from_origin']),
                    "status": rs['status'],
                }
                for rs in payload.get("station_details")
            ],
            "schedules" : existing_schedules
        }
        # Index/upsert the document
        await routes_repo.index(es_document)
        await es_client.close()
        return True
    except Exception as e:
        print(f"ES indexing error: {e}")
        return False


async def run_worker() -> None:
    consumer = build_consumer(
        topic=settings.KAFKA_ROUTE_TOPIC,
        group_id=settings.KAFKA_ROUTE_TOPIC_CONSUMER_GROUP,
        client_id=f"{settings.KAFKA_CLIENT_ID}-routes-consumer",
    )
    await consumer.start()
    app_logger.info("routes_consumer_worker started")
    try:
        async for message in consumer:
            try:
                payload = json.loads(message.value.decode("utf-8"))
                topic_name = message.topic
                print(f"Topic: {topic_name}, Payload: {payload}")
                # Index to Elasticsearch
                success = await index_to_elasticsearch(payload)
                if success:
                    print(f"Successfully added route details into index-route using Route-ID: {payload.get('route_id')}")
                else:
                    print(f"Fail to add route details into index-route using Route-ID: {payload.get('route_id')}")
                await consumer.commit()                
            except Exception as exc:
                print(f"routes_consumer_worker error: {exc}")
                await asyncio.sleep(0.2)
    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(run_worker())
