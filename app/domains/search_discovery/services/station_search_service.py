
from app.core.exceptions import BaseAppException
from app.core.response import (
    standardize_response, 
)
from app.infrastructure.elasticsearch.client import ElasticsearchClient
from app.infrastructure.elasticsearch.repositories.station_repository import StationElasticsearchRepository


class StationSearchService:

    def __init__(self, es_client: ElasticsearchClient):
        self.station_es_repo = StationElasticsearchRepository(es_client)


    async def search_stations(
        self,
        *,
        q: str,
        size: int,
    ) -> dict:
        
        try:
            es_result = await self.station_es_repo.search_dropdown(
                query=q,
                size=size,
            )
        except Exception as e:
            return standardize_response(
                status_code=503,
                messages=["Search service temporarily unavailable"],
            )

        try:
            
            hits = es_result.get("hits", {}).get("hits", [])
            results = []
            seen_codes = set()

            for hit in hits:
                src = hit.get("_source", {}) or {}
                code = (src.get("code") or "").strip().upper()
                if not code or code in seen_codes:
                    continue
                seen_codes.add(code)
                station_id = src.get("station_id")
                name = (src.get("name") or "").strip()
                city = (src.get("city") or "").strip()
                results.append(
                    {
                        "station_id": station_id,
                        "code": code,
                        "name": name,
                        "city": city,
                        "label": f"{code} - {name}, {city}" if city else f"{code} - {name}",
                    }
                )

            if results:
                return standardize_response(
                    status_code=200,
                    messages=["Stations found"],
                    data={
                        "query": q,
                        "count": len(results),
                        "results": results,
                    },
                )
            else:
                return standardize_response(
                    status_code=404,
                    messages=["Stations not found"],
                )
            
        except Exception as e:
            return standardize_response(
                status_code=500,
                messages=[f"{str(e)}"],
            )
        
