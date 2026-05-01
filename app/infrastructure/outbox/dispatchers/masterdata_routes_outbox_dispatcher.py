
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
        es_document = {
            "train_id": train_details.get("train_id", 0),
            "train_name": train_details.get("train_name", ""),
            "train_number": train_details.get("train_number", ""),
            "seatSummary" : seatSummary,
            "routes" : [
                {
                    "id": rs['id'],
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
            "schedules" : []
        }
        # Index/upsert the document
        await routes_repo.index(es_document)
        app_logger.info(f"Indexed routes to ES using RouteID: {route_id}, TrainID: {train_details.get("train_id", 0)}")
        await es_client.close()
        return True
    except Exception as e:
        app_logger.error(f"ES indexing error: {e}")
        return False


async def run_worker() -> None:
    consumer = build_consumer(
        topic=settings.MASTERDATA_ROUTE_EVENT_TOPIC,
        group_id=settings.MASTERDATA_ROUTE_CONSUMER_GROUP,
        client_id=f"{settings.KAFKA_CLIENT_ID}-masterdata-routes-consumer",
    )
    await consumer.start()
    app_logger.info("masterdata_routes_dispatch_consumer_worker started")
    try:
        async for message in consumer:
            try:
                payload = json.loads(message.value.decode("utf-8"))
                app_logger.info(f"Received payload: {payload}")
                # Index to Elasticsearch
                success = await index_to_elasticsearch(payload)
                if success:
                    app_logger.info(f"Successfully indexed route_id: {payload.get('route_id')}, train_id: {payload.get("train_details").get("train_id", 0)}")
                else:
                    app_logger.error(f"Failed to index route_id: {payload.get('route_id')}, train_id: {payload.get("train_details").get("train_id", 0)}")
                
                await consumer.commit()                
            except Exception as exc:
                app_logger.error(f"masterdata_routes_dispatch_consumer_worker error: {exc}")
                await asyncio.sleep(0.2)
    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(run_worker())
