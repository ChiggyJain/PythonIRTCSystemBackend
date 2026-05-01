
from typing import Any, Optional
from app.common.utils.logger import app_logger
from app.infrastructure.elasticsearch.client import ElasticsearchClient
from app.infrastructure.elasticsearch.mappings.routes_mapping import ROUTES_INDEX_MAPPING


class RoutesElasticsearchRepository:
    
    def __init__(self, es_client: ElasticsearchClient):
        self.es = es_client
    

    async def create_index_if_not_exists(self) -> None:
        try:
            exists = await self.es.client.indices.exists(index=self.es.index_name)
            if not exists:
                await self.es.client.indices.create(
                    index=self.es.index_name,
                    body=ROUTES_INDEX_MAPPING
                )
                app_logger.info(f"Created ES index: {self.es.index_name}")
        except Exception as e:
            app_logger.error(f"Failed to create ES index: {e}")
            raise
    
    
    async def index(self, document: dict[str, Any]) -> dict:
        doc_id = str(document.get("train_id"))
        return await self.es.index(document=document, doc_id=doc_id)
    

    async def get_by_id(self, train_id: int) -> Optional[dict]:
        return await self.es.get(doc_id=str(train_id))
    

    async def delete(self, train_id: int) -> bool:
        return await self.es.delete(doc_id=str(train_id))
    

    