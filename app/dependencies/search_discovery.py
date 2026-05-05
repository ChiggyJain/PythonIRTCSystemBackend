
from fastapi import Request
from app.core.settings import get_settings
from app.domains.search_discovery.services.train_search_service import TrainSearchService
from app.domains.search_discovery.services.station_search_service import StationSearchService


def get_train_search_service(request: Request) -> TrainSearchService:
    es_client = request.app.state.routes_es_client
    return TrainSearchService(es_client=es_client)

def get_station_search_service(request: Request) -> StationSearchService:
    es_client = request.app.state.stations_es_client
    return StationSearchService(es_client=es_client)
