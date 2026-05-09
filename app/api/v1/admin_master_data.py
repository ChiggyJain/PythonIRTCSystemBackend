
from fastapi import APIRouter, Depends, Request
from app.common.decorators.feature_control import feature_control
from app.common.utils.ratelimiter import rate_limiter
from app.core.exceptions import BaseAppException
from app.core.response import success_response
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
        "name": "user:stations:create",
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
async def create_station(
    body: StationCreateRequest,
    request: Request,
    admin_user_details: dict = Depends(get_current_admin_user_details_from_access_token),
    service: StationsService = Depends(get_stations_service),
):
    
    payload = body.model_dump()
    payload["user_id"] = int(admin_user_details.get("sub"))
    payload["correlation_id"] = request.headers.get("x-correlation-id")
    payload["request_id"] = request.headers.get("x-request-id")
    return await service.create_station(payload=payload)

router.add_api_route(
    "/stations",
    create_station,
    methods=["POST"],
    route_class_override=FeatureAPIRoute,
)



@feature_control(
    {
        "name": "user:trains:create",
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
async def create_train(
    body: TrainCreateRequest,
    request: Request,
    admin_user_details: dict = Depends(get_current_admin_user_details_from_access_token),
    service: TrainsService = Depends(get_trains_service),
):
    
    payload = body.model_dump()
    payload["user_id"] = int(admin_user_details.get("sub"))
    payload["correlation_id"] = request.headers.get("x-correlation-id")
    payload["request_id"] = request.headers.get("x-request-id")
    return await service.create_train(payload=payload)

router.add_api_route(
    "/trains",
    create_train,
    methods=["POST"],
    route_class_override=FeatureAPIRoute,
)


@feature_control(
    {
        "name": "user:train:route:create",
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
async def create_train_route(
    body: TrainRouteCreateRequest,
    request: Request,
    admin_user_details: dict = Depends(get_current_admin_user_details_from_access_token),
    service: RoutesService = Depends(get_routes_service),
):

    payload = body.model_dump()
    payload["user_id"] = int(admin_user_details.get("sub"))
    payload["correlation_id"] = request.headers.get("x-correlation-id")
    payload["request_id"] = request.headers.get("x-request-id")
    return await service.create_train_route(payload=payload)

router.add_api_route(
    "/train-routes",
    create_train_route,
    methods=["POST"],
    route_class_override=FeatureAPIRoute,
)


@feature_control(
    {
        "name": "user:train:schedule:create",
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
async def create_train_schedule(
    body: TrainScheduleCreateRequest,
    request: Request,
    admin_user_details: dict = Depends(get_current_admin_user_details_from_access_token),
    service: TrainSchedulesService = Depends(get_train_schedules_service),
):
    
    payload = body.model_dump()
    payload["user_id"] = int(admin_user_details.get("sub"))
    payload["correlation_id"] = request.headers.get("x-correlation-id")
    payload["request_id"] = request.headers.get("x-request-id")
    return await service.create_train_schedule(payload=payload)

router.add_api_route(
    "/train-schedules",
    create_train_schedule,
    methods=["POST"],
    route_class_override=FeatureAPIRoute,
)