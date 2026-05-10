
from fastapi import APIRouter, Depends, Request
from app.common.decorators.feature_control import feature_control
from app.core.routing.feature_route import FeatureAPIRoute
from app.core.settings import get_settings
from app.common.security.token_decoder import (
    get_current_admin_user_details_from_access_token
)
from app.dependencies.master_data import (
    get_stations_service, 
    get_trains_service,
    get_routes_service,
    get_train_schedules_service,
)
from app.domains.master_data.schemas.stations_schemas import StationCreateRequest
from app.domains.master_data.services.stations_services import StationsService
from app.domains.master_data.schemas.trains_schemas import TrainCreateRequest
from app.domains.master_data.services.trains_services import TrainsService
from app.domains.master_data.schemas.routes_schemas import TrainRouteCreateRequest
from app.domains.master_data.services.routes_services import RoutesService
from app.domains.master_data.schemas.schedules_schemas import TrainScheduleCreateRequest
from app.domains.master_data.services.schedules_services import TrainSchedulesService


settings = get_settings()
router = APIRouter()


@feature_control(
    {
        "name": "user:booking:create",
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
async def create_booking(
    body: StationCreateRequest,
    request: Request,
    admin_user_details: dict = Depends(get_current_admin_user_details_from_access_token),
    service: StationsService = Depends(get_stations_service),
):
    
    payload = body.model_dump()
    payload["user_id"] = int(admin_user_details.get("sub"))
    payload["correlation_id"] = request.headers.get("x-correlation-id")
    payload["request_id"] = request.headers.get("x-request-id")
    return await service.create_booking_details(payload=payload)

router.add_api_route(
    "/stations",
    create_booking,
    methods=["POST"],
    route_class_override=FeatureAPIRoute,
)



