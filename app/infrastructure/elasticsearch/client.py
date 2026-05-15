
from typing import Any, Optional
from elasticsearch import AsyncElasticsearch, NotFoundError, RequestError
from app.common.utils.logger import app_logger
from app.infrastructure.elasticsearch.config import get_elasticsearch_config


class ElasticsearchClient:
    
    def __init__(self, client: AsyncElasticsearch):
        self.client = client
    

    async def create_index_if_not_exists(self, index_name: str, mapping: dict[str, Any]) -> None:
        try:
            exists = await self.client.indices.exists(index=index_name)
            if not exists:
                await self.client.indices.create(index=index_name, body=mapping)
                app_logger.info(f"Created ES index: {index_name}")
        except Exception as e:
            app_logger.error(f"Unexpected error creating ES index {index_name}: {e}")
            raise
    

    async def index_document(
        self,
        index_name: str,
        document: dict[str, Any],
        doc_id: Optional[str] = None,
    ) -> dict:
        try:
            return await self.client.index(
                index=index_name,
                id=doc_id,
                document=document,
                refresh=True
            )
        except Exception as e:
            app_logger.error(f"Unexpected ES index error for {index_name}: {e}")
            raise
    

    async def get_document(self, index_name: str, doc_id: str) -> Optional[dict]:
        try:
            return await self.client.get(
                index=index_name, 
                id=doc_id
            )
        except Exception as e:
            app_logger.error(f"Unexpected ES get error for {index_name}: {e}")
            raise
    

    async def search_document(self, index_name: str, query: dict) -> dict:
        try:
            return await self.client.search(index=index_name, body=query)
        except Exception as e:
            app_logger.error(f"Unexpected ES search error for {index_name}: {e}")
            raise
    
    
    async def delete_document(self, index_name: str, doc_id: str) -> bool:
        try:
            await self.client.delete(
                index=index_name, 
                id=doc_id, 
                refresh=True
            )
            return True
        except Exception as e:
            app_logger.error(f"Unexpected ES delete error for {index_name}: {e}")
            raise
    

    async def update_document(self, index_name: str, doc_id: str, body: dict[str, Any]) -> dict:
        try:
            return await self.client.update(
                index=index_name, 
                id=doc_id, 
                body=body, 
                refresh=True
            )
        except Exception as e:
            app_logger.error(f"Unexpected ES update error for {index_name}: {e}")
            raise


    async def close(self) -> None:
        await self.client.close()



def build_elasticsearch_client() -> ElasticsearchClient:
    config = get_elasticsearch_config()
    client_kwargs = {
        "hosts": [config.url],
        "verify_certs": config.verify_certs,
        "request_timeout": config.request_timeout_seconds,
    }
    if config.username and config.password:
        client_kwargs["basic_auth"] = (config.username, config.password)
    client = AsyncElasticsearch(**client_kwargs)
    app_logger.info("ES client instances created")
    return ElasticsearchClient(client=client)