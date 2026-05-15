
from typing import Any, Optional
from app.common.utils.logger import app_logger
from app.infrastructure.elasticsearch.client import ElasticsearchClient
from app.infrastructure.elasticsearch.mappings.routes_mapping import ROUTES_INDEX_MAPPING


class RoutesElasticsearchRepository:
    
    def __init__(self, es_client_instances: ElasticsearchClient, index_name: str):
        self.es_client_instances = es_client_instances
        self.index_name = index_name
    

    async def create_index_if_not_exists(self) -> None:
        await self.es_client_instances.create_index_if_not_exists(
            self.index_name, 
            ROUTES_INDEX_MAPPING
        )
    
    
    async def index_document(self, doc_id: str, document: dict[str, Any]) -> dict:
        return await self.es_client_instances.index_document(
            index_name=self.index_name,
            document=document,
            doc_id=doc_id
        )    
    

    async def get_document(self, doc_id: str) -> Optional[dict]:
        return await self.es_client_instances.get_document(
            index_name=self.index_name,
            doc_id=doc_id
        )
        

    async def upsert_schedule(
        self,
        train_id: str,
        schedules: dict[str, Any]
    ) -> dict:
        
        return await self.es_client_instances.update_document(
            index_name=self.index_name,
            doc_id=train_id,
            body={
                "script": {
                    "source": """
                        if(ctx._source.schedules == null){
                            ctx._source.schedules = [];
                        }
                        String targetId = params.schedules.schedule_id.toString();
                        boolean found = false;
                        for (int i = 0; i < ctx._source.schedules.size(); i++) {
                            if (
                                ctx._source.schedules[i].schedule_id != null &&
                                ctx._source.schedules[i].schedule_id.toString() == targetId
                            ) {
                                for (entry in params.schedules.entrySet()) {
                                    ctx._source.schedules[i][entry.getKey()] = entry.getValue();
                                }
                                found = true;
                                break;
                            }
                        }
                        if (!found) {
                            ctx._source.schedules.add(params.schedules);
                        }
                    """,
                    "params": {
                        "schedules": schedules
                    }
                }
            }
        )
    

    async def search_trains(
        self,
        *,
        source_query: str,
        destination_query: str,
        journey_date: str,
        page: int = 1,
        size: int = 20,
    ) -> dict:
        
        from_value = (page - 1) * size

        search_body = {
            "track_total_hits": True,
            "from": from_value,
            "size": size,
            "_source": [
                "train_id",
                "train_number",
                "train_name",
                "seatSummary",
                "routes.route_id",
                "routes.station_id",
                "routes.name",
                "routes.code",
                "routes.city",
                "routes.sequence_number",
                "routes.arrival_time",
                "routes.departure_time",
                "routes.distance_from_origin",
                "schedules.schedule_id",
                "schedules.departure_date",
                "schedules.available",
                "schedules.locked",
                "schedules.booked",
                "schedules.status",
            ],
            "query": {
                "bool": {
                    "must": [
                        {
                            "nested": {
                                "path": "routes",
                                "query": {
                                    "term": {
                                        "routes.code": source_query
                                    }
                                },
                                "inner_hits": {
                                    "name": "source_match",
                                    "size": 1
                                }
                            }
                        },
                        {
                            "nested": {
                                "path": "routes",
                                "query": {
                                    "term": {
                                        "routes.code": destination_query
                                    }
                                },
                                "inner_hits": {
                                    "name": "destination_match",
                                    "size": 1
                                }
                            }
                        },
                        {
                            "nested": {
                                "path": "schedules",
                                "query": {
                                    "bool": {
                                        "must": [
                                            {
                                                "range": {
                                                    "schedules.departure_date": {
                                                        "gte": journey_date
                                                    }
                                                }
                                            },
                                            {
                                                "term": {
                                                    "schedules.status": "A"
                                                }
                                            }
                                        ]
                                    }
                                },
                                "inner_hits": {
                                    "name": "matched_schedule",
                                    "size": 1,
                                    "sort": [
                                        {
                                            "schedules.departure_date": {
                                                "order": "asc"
                                            }
                                        }
                                    ]
                                }
                            }
                        }
                    ]
                }
            },
            "sort": [
                {
                    "schedules.departure_date": {
                        "order": "asc",
                        "mode": "min",
                        "nested": {
                            "path": "schedules",
                            "filter": {
                                "bool": {
                                    "must": [
                                        {
                                            "range": {
                                                "schedules.departure_date": {
                                                    "gte": journey_date
                                                }
                                            }
                                        },
                                        {
                                            "term": {
                                                "schedules.status": "A"
                                            }
                                        }
                                    ]
                                }
                            }
                        }
                    }
                },
                {
                    "schedules.available": {
                        "order": "desc",
                        "mode": "max",
                        "nested": {
                            "path": "schedules",
                            "filter": {
                                "bool": {
                                    "must": [
                                        {
                                            "range": {
                                                "schedules.departure_date": {
                                                    "gte": journey_date
                                                }
                                            }
                                        },
                                        {
                                            "term": {
                                                "schedules.status": "A"
                                            }
                                        }
                                    ]
                                }
                            }
                        }
                    }
                },
                {"train_number": {"order": "asc"}}
            ]
        }

        return await self.es_client_instances.search_document(
            index_name=self.index_name,
            query=search_body
        )

        