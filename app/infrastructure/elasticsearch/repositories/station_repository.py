
from typing import Any, Optional
from app.common.utils.logger import app_logger
from app.infrastructure.elasticsearch.client import ElasticsearchClient
from app.infrastructure.elasticsearch.mappings.stations_mapping import STATIONS_INDEX_MAPPING


class StationElasticsearchRepository:
    
    def __init__(self, es_client: ElasticsearchClient):
        self.es = es_client
    

    async def create_index_if_not_exists(self) -> None:
        try:
            exists = await self.es.client.indices.exists(index=self.es.index_name)
            if not exists:
                await self.es.client.indices.create(
                    index=self.es.index_name,
                    body=STATIONS_INDEX_MAPPING
                )
                app_logger.info(f"Created ES index: {self.es.index_name}")
        except Exception as e:
            app_logger.error(f"Failed to create ES index: {e}")
            raise
    
    async def index(self, document: dict[str, Any]) -> dict:
        doc_id = str(document.get("station_id"))
        return await self.es.index(document=document, doc_id=doc_id)
    

    async def get_by_id(self, station_id: int) -> Optional[dict]:
        return await self.es.get(doc_id=str(station_id))
    
    async def delete(self, station_id: int) -> bool:
        return await self.es.delete(doc_id=str(station_id))
    

    async def search(
        self,
        query: str,
        page: int = 1,
        size: int = 20,
    ) -> dict:
        
        search_body = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": [
                        "name^3",
                        "code^2",
                        "city^2",
                        "state"
                    ],
                    "fuzziness": "AUTO",
                    "prefix_length": 2,
                    "type": "best_fields"
                }
            },
            "from": (page - 1) * size,
            "size": size
        }
        return await self.es.search(query=search_body)
    
    
    async def autocomplete(self, prefix: str, size: int = 10) -> dict:
        search_body = {
            "suggest": {
                "station-suggest": {
                    "text": prefix,
                    "completion": {
                        "field": "name.suggest",
                        "size": size,
                        "skip_duplicates": True
                    }
                }
            }
        }
        return await self.es.search(query=search_body)
    

    async def search_by_code(self, code: str) -> dict:
        search_body = {
            "query": {
                "term": {
                    "code": code.lower()
                }
            }
        }
        return await self.es.search(query=search_body)
    

    async def filter_by_city(self, city: str) -> dict:
        search_body = {
            "query": {
                "term": {
                    "city": city.lower()
                }
            }
        }
        return await self.es.search(query=search_body)
    

    async def filter_by_state(self, state: str) -> dict:
        search_body = {
            "query": {
                "term": {
                    "state": state.lower()
                }
            }
        }
        return await self.es.search(query=search_body)