
from typing import Annotated
from fastapi import APIRouter, Depends, Query
from app.core.response import success_response
from app.core.routing.feature_route import FeatureAPIRoute
from app.common.decorators.feature_control import feature_control
from app.dependencies.search_discovery import (
    get_train_search_service,
    get_station_search_service
)
from app.domains.search_discovery.schemas.station_search_schemas import StationSearchQueryRequest
from app.domains.search_discovery.services.station_search_service import StationSearchService
from app.domains.search_discovery.schemas.train_search_schemas import TrainSearchQueryRequest
from app.domains.search_discovery.services.train_search_service import TrainSearchService


router = APIRouter()


@feature_control(
    {
        "name": "user:search:stations",
        "logging": {
            "console": True, 
            "file": True
        },
        "rate_limit": {
            "limit": 100, 
            "window": 60
        },
    }
)
async def search_stations(
    query: Annotated[StationSearchQueryRequest, Depends()],
    service: StationSearchService = Depends(get_station_search_service),
):
    return await service.search_stations(
        q=query.q,
        size=query.size,
    )
    
router.add_api_route(
    "/search/stations",
    search_stations,
    methods=["GET"],
    route_class_override=FeatureAPIRoute,
)


@feature_control(
    {
        "name": "user:search:trains",
        "logging": {
            "console": True,
            "file": True,
        },
        "rate_limit": {
            "limit": 100,
            "window": 60,
        },
    }
)
async def search_trains(
    query: Annotated[TrainSearchQueryRequest, Depends()],
    service: TrainSearchService = Depends(get_train_search_service),
):
    
    return await service.search_trains(
        source=query.source,
        destination=query.destination,
        journey_date=str(query.journey_date),
        page=query.page,
        size=query.size,
    )

router.add_api_route(
    "/search/trains",
    search_trains,
    methods=["GET"],
    route_class_override=FeatureAPIRoute,
)
