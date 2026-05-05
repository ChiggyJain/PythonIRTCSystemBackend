
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
    
    
    async def search_dropdown(
        self,
        *,
        query: str,
        size: int = 10,
    ) -> dict:
        
        q = query.strip()
        q_upper = q.upper()

        search_body = {
            
            "size": size,
            "track_total_hits": False,
            "_source": ["station_id", "name", "code", "city"],
            "query": {
                "bool": {
                    "should": [
                        {
                            "term": {
                                "code": {
                                    "value": q_upper,
                                    "boost": 12
                                }
                            }
                        },
                        {
                            "prefix": {
                                "code": {
                                    "value": q_upper,
                                    "boost": 8
                                }
                            }
                        },
                        {
                            "match_phrase_prefix": {
                                "name": {
                                    "query": q,
                                    "boost": 5
                                }
                            }
                        },
                        {
                            "match_phrase_prefix": {
                                "city": {
                                    "query": q,
                                    "boost": 4
                                }
                            }
                        },
                        {
                            "multi_match": {
                                "query": q,
                                "fields": ["name^3", "city^2", "code^4"],
                                "fuzziness": "AUTO",
                                "prefix_length": 1,
                                "minimum_should_match": "75%",
                                "type": "best_fields",
                                "boost": 2
                            }
                        }
                    ],
                    "minimum_should_match": 1
                }
            },
            "sort": [
                {"_score": {"order": "desc"}},
                {"name.keyword": {"order": "asc"}}
            ]
        }

        return await self.es.search(query=search_body)
