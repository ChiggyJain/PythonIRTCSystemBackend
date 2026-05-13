
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
    

    async def upsert_schedule(
        self,
        train_id: int,
        schedules: dict[str, Any]
    ) -> dict:
        
        return await self.es.client.update(
            index=self.es.index_name,
            id=str(train_id),
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
            },
            refresh=True
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

        return await self.es.search(query=search_body)

        