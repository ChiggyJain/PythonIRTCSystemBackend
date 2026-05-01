
from fastapi import APIRouter, Depends, Query
from app.core.response import success_response
from app.core.routing.feature_route import FeatureAPIRoute
from app.common.decorators.feature_control import feature_control
from app.dependencies.search_discovery import get_train_search_service
from app.domains.search_discovery.schemas.train_search_schemas import TrainSearchQueryRequest
from app.domains.search_discovery.services.train_search_service import TrainSearchService


router = APIRouter()


@feature_control(
    {
        "name": "v1.search.trains",
        "logging": {
            "console": True,
            "file": True,
        },
        "rate_limit": {
            "limit": 120,
            "window": 60,
        },
    }
)
async def search_trains(
    source: str = Query(..., description="Source station query"),
    destination: str = Query(..., description="Destination station query"),
    journey_date: str = Query(..., description="Journey date in YYYY-MM-DD"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    service: TrainSearchService = Depends(get_train_search_service),
):
    
    # validate using your schema rules
    query = TrainSearchQueryRequest(
        source=source,
        destination=destination,
        journey_date=journey_date,
        page=page,
        size=size,
    )
    
    data = await service.search_trains(
        source=query.source,
        destination=query.destination,
        journey_date=str(query.journey_date),
        page=query.page,
        size=query.size,
    )

    return success_response(
        data=data,
        messages=["Train search results fetched successfully"],
        status_code=200,
    )


router.add_api_route(
    "/search/trains",
    search_trains,
    methods=["GET"],
    route_class_override=FeatureAPIRoute,
)
