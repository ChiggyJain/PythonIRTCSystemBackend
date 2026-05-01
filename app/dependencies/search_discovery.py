
from fastapi import Request
from app.core.settings import get_settings
from app.domains.search_discovery.services.train_search_service import TrainSearchService


def get_train_search_service(request: Request) -> TrainSearchService:
    es_client = request.app.state.routes_es_client
    return TrainSearchService(es_client=es_client)