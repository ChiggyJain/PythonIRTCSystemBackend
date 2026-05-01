
from app.core.settings import get_settings
from app.domains.search_discovery.services.train_search_service import TrainSearchService
from app.infrastructure.elasticsearch.client import build_elasticsearch_client


def get_train_search_service() -> TrainSearchService:
    settings = get_settings()
    es_client = build_elasticsearch_client(settings.ELASTICSEARCH_ROUTES_INDEX)
    return TrainSearchService(es_client=es_client)