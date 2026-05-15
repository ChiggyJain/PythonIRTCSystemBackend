
from fastapi import Request
from app.core.settings import get_settings
from app.domains.search_discovery.services.train_search_service import TrainSearchService
from app.domains.search_discovery.services.station_search_service import StationSearchService


def get_train_search_service(request: Request) -> TrainSearchService:
    es_client_instances = request.app.state.es_client_instances
    return TrainSearchService(
        es_client_instances=es_client_instances
    )

def get_station_search_service(request: Request) -> StationSearchService:
    es_client_instances = request.app.state.es_client_instances
    return StationSearchService(
        es_client_instances=es_client_instances
    )
