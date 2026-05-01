
from datetime import datetime
from app.core.exceptions import BaseAppException
from app.infrastructure.elasticsearch.client import ElasticsearchClient
from app.infrastructure.elasticsearch.repositories.routes_repository import RoutesElasticsearchRepository


class TrainSearchService:

    def __init__(self, es_client: ElasticsearchClient):
        self.routes_es_repo = RoutesElasticsearchRepository(es_client)


    async def search_trains(
        self,
        *,
        source: str,
        destination: str,
        journey_date: str,
        page: int,
        size: int,
    ) -> dict:
        
        try:
            es_result = await self.routes_es_repo.search_trains(
                source_query=source,
                destination_query=destination,
                journey_date=journey_date,
                page=page,
                size=size,
            )
        except Exception:
            raise BaseAppException(
                status_code=503,
                messages=["Search service temporarily unavailable"],
            )

        print(f"es_result: {es_result}")
        hits_block = es_result.get("hits", {})
        total_block = hits_block.get("total", {})
        total_value = total_block.get("value", 0) if isinstance(total_block, dict) else 0
        hits = hits_block.get("hits", [])

        results = []
        for hit in hits:
            
            source_doc = hit.get("_source", {}) or {}
            inner_hits = hit.get("inner_hits", {}) or {}

            source_matches = (
                inner_hits.get("source_match", {})
                .get("hits", {})
                .get("hits", [])
            )
            destination_matches = (
                inner_hits.get("destination_match", {})
                .get("hits", {})
                .get("hits", [])
            )
            schedule_matches = (
                inner_hits.get("matched_schedule", {})
                .get("hits", {})
                .get("hits", [])
            )

            if not source_matches or not destination_matches or not schedule_matches:
                continue

            source_station = self._pick_best_route_match(source_matches)
            destination_station = self._pick_best_route_match(destination_matches)
            matched_schedule = (schedule_matches[0].get("_source", {}) or {})

            if not source_station or not destination_station:
                continue

            source_seq = int(source_station.get("sequence_number", 0))
            destination_seq = int(destination_station.get("sequence_number", 0))

            # enforce journey direction
            if source_seq <= 0 or destination_seq <= 0 or source_seq >= destination_seq:
                continue

            travel_distance = self._compute_distance(
                source_station.get("distance_from_origin"),
                destination_station.get("distance_from_origin"),
            )
            duration_minutes = self._compute_duration_minutes(
                source_station.get("departure_time"),
                destination_station.get("arrival_time"),
            )

            total_available = int(matched_schedule.get("available", 0))
            availability_status = "AVAILABLE" if total_available > 0 else "WAITLIST"

            result_item = {
                "train_id": source_doc.get("train_id"),
                "train_number": source_doc.get("train_number"),
                "train_name": source_doc.get("train_name"),
                "journey_date": journey_date,
                "source_station": {
                    "station_id": source_station.get("station_id"),
                    "code": source_station.get("code"),
                    "name": source_station.get("name"),
                    "city": source_station.get("city"),
                    "sequence_number": source_seq,
                    "departure_time": source_station.get("departure_time"),
                },
                "destination_station": {
                    "station_id": destination_station.get("station_id"),
                    "code": destination_station.get("code"),
                    "name": destination_station.get("name"),
                    "city": destination_station.get("city"),
                    "sequence_number": destination_seq,
                    "arrival_time": destination_station.get("arrival_time"),
                },
                "travel": {
                    "duration_minutes": duration_minutes,
                    "distance_km": travel_distance,
                },
                "availability_summary": {
                    "status": availability_status,
                    "total_available": total_available,
                },
                "booking_context": {
                    "schedule_id": matched_schedule.get("id"),
                    "route_id": None,  # optional, keep None if not indexed in ES doc
                },
            }

            results.append(result_item)

        returned = len(results)
        has_next = (page * size) < total_value

        return {
            "query": {
                "source": source,
                "destination": destination,
                "journey_date": journey_date,
            },
            "pagination": {
                "page": page,
                "size": size,
                "returned": returned,
                "total": total_value,
                "has_next": has_next,
            },
            "results": results,
        }

    def _pick_best_route_match(self, route_hits: list[dict]) -> dict | None:
        if not route_hits:
            return None
        best = route_hits[0]
        return best.get("_source", {}) or {}

    def _compute_distance(self, source_distance: float | int | None, destination_distance: float | int | None) -> float:
        if source_distance is None or destination_distance is None:
            return 0.0
        value = float(destination_distance) - float(source_distance)
        return round(value if value > 0 else 0.0, 2)

    def _compute_duration_minutes(self, source_departure: str | None, destination_arrival: str | None) -> int:
        if not source_departure or not destination_arrival:
            return 0
        fmt = "%H:%M:%S"
        try:
            dep = datetime.strptime(source_departure, fmt)
            arr = datetime.strptime(destination_arrival, fmt)
            minutes = int((arr - dep).total_seconds() / 60)
            if minutes >= 0:
                return minutes
            # overnight case
            return minutes + (24 * 60)
        except Exception:
            return 0
