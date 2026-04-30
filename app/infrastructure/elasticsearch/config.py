
from functools import lru_cache
from pydantic import BaseModel
from app.core.settings import get_settings


class ElasticsearchConfig(BaseModel):
    url: str = "http://127.0.0.1:9200"
    username: str = ""
    password: str = ""
    verify_certs: bool = False
    request_timeout_seconds: int = 10

@lru_cache()
def get_elasticsearch_config() -> ElasticsearchConfig:
    settings = get_settings()
    return ElasticsearchConfig(
        url=settings.ELASTICSEARCH_URL,
        username=settings.ELASTICSEARCH_USERNAME,
        password=settings.ELASTICSEARCH_PASSWORD,
        verify_certs=settings.ELASTICSEARCH_VERIFY_CERTS,
        request_timeout_seconds=settings.ELASTICSEARCH_REQUEST_TIMEOUT_SECONDS,
    )