

from typing import Any, Optional
from elasticsearch import AsyncElasticsearch
from app.common.utils.logger import app_logger
from app.infrastructure.elasticsearch.config import get_elasticsearch_config


class ElasticsearchClient:
    
    def __init__(self, client: AsyncElasticsearch, index_name: str):
        self.client = client
        self.index_name = index_name
    

    async def index(
        self,
        document: dict[str, Any],
        doc_id: Optional[str] = None,
    ) -> dict:
        
        return await self.client.index(
            index=self.index_name,
            id=doc_id,
            document=document,
        )
    

    async def get(self, doc_id: str) -> Optional[dict]:
        try:
            return await self.client.get(index=self.index_name, id=doc_id)
        except Exception as e:
            app_logger.error(f"ES get error: {e}")
            return None
    

    async def search(self, query: dict) -> dict:
        return await self.client.search(index=self.index_name, body=query)
    
    async def delete(self, doc_id: str) -> bool:
        try:
            await self.client.delete(index=self.index_name, id=doc_id)
            return True
        except Exception as e:
            app_logger.error(f"ES delete error: {e}")
            return False
    
    async def close(self) -> None:
        await self.client.close()


def build_elasticsearch_client(index_name: str | None) -> ElasticsearchClient:
    config = get_elasticsearch_config()
    client_kwargs = {
        "hosts": [config.url],
        "verify_certs": config.verify_certs,
        "request_timeout": config.request_timeout_seconds,
    }
    if config.username and config.password:
        client_kwargs["basic_auth"] = (config.username, config.password)
    client = AsyncElasticsearch(**client_kwargs)
    app_logger.info(f"ES client created for index: {index_name}")
    return ElasticsearchClient(client=client, index_name=index_name)