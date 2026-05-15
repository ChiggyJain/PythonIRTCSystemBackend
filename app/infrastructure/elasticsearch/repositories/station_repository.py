
from typing import Any, Optional
from app.common.utils.logger import app_logger
from app.infrastructure.elasticsearch.client import ElasticsearchClient
from app.infrastructure.elasticsearch.mappings.stations_mapping import STATIONS_INDEX_MAPPING


class StationElasticsearchRepository:
    
    def __init__(self, es_client_instances: ElasticsearchClient, index_name: str):
        self.es_client_instances = es_client_instances
        self.index_name = index_name
    

    async def create_index_if_not_exists(self) -> None:
        await self.es_client_instances.create_index_if_not_exists(
            self.index_name, STATIONS_INDEX_MAPPING
        )
    

    async def index_document(self, doc_id: str, document: dict[str, Any]) -> dict:
        return await self.es_client_instances.index_document(
            index_name=self.index_name,
            document=document,
            doc_id=doc_id
        )    
    
    async def search_stations(
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

        return await self.es_client_instances.search_document(
            index_name=self.index_name,
            query=search_body
        )
