
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

    return success_response(
        status_code=201,
        messages=["Station created successfully"],
        data=result,
    )


router.add_api_route(
    "/stations",
    create_station,
    methods=["POST"],
    route_class_override=FeatureAPIRoute,
)


# --------------------------------
# trains with seats create process
# --------------------------------

@feature_control(
    {
        "name": "v1.admin.master_data.trains.create",
        "logging": {
            "console": True,
            "file": True,
        },
        "rate_limit": {
            # IP-based route-level limiter
            "limit": 30,
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
    
    admin_user_id = int(admin_user_details.get("sub"))

    # User-level limiter for train creation
    user_rate_key = f"ratelimit:v1.admin.master_data.trains.create:user:{admin_user_id}"
    allowed = await rate_limiter.check_window_limit(
        key=user_rate_key,
        limit=settings.MASTERDATA_TRAIN_CREATE_USER_RATE_LIMIT,
        window=settings.MASTERDATA_TRAIN_CREATE_USER_RATE_WINDOW_SECONDS,
    )
    if not allowed:
        raise BaseAppException(
            status_code=429,
            messages=["Too many train create requests for this admin. Please try again later."],
        )

    result = await service.create_train(
        train_number=body.train_number,
        train_name=body.train_name,
        coach_name=body.coach_name,
        total_seats=body.total_seats,
        seat_details=[seat.model_dump() for seat in body.seat_details],
        admin_user_id=admin_user_id,
        correlation_id=request.headers.get("x-correlation-id"),
        request_id=request.headers.get("x-request-id"),
    )

    return success_response(
        status_code=201,
        messages=["Train created successfully"],
        data=result,
    )

router.add_api_route(
    "/trains",
    create_train,
    methods=["POST"],
    route_class_override=FeatureAPIRoute,
)



# -----------------------------------------
# train route with stations create process
# -----------------------------------------

@feature_control(
    {
        "name": "v1.admin.master_data.train_routes.create",
        "logging": {
            "console": True,
            "file": True,
        },
        "rate_limit": {
            "limit": 30,
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
    
    admin_user_id = int(admin_user_details.get("sub"))

    user_rate_key = f"ratelimit:v1.admin.master_data.train_routes.create:user:{admin_user_id}"
    allowed = await rate_limiter.check_window_limit(
        key=user_rate_key,
        limit=settings.MASTERDATA_ROUTE_CREATE_USER_RATE_LIMIT,
        window=settings.MASTERDATA_ROUTE_CREATE_USER_RATE_WINDOW_SECONDS,
    )
    if not allowed:
        raise BaseAppException(
            status_code=429,
            messages=["Too many train-route create requests for this admin. Please try again later."],
        )

    result = await service.create_train_route(
        train_id=body.train_id,
        station_details=[row.model_dump() for row in body.station_details],
        admin_user_id=admin_user_id,
        correlation_id=request.headers.get("x-correlation-id"),
        request_id=request.headers.get("x-request-id"),
    )

    return success_response(
        status_code=201,
        messages=["Train route created successfully"],
        data=result,
    )


router.add_api_route(
    "/train-routes",
    create_train_route,
    methods=["POST"],
    route_class_override=FeatureAPIRoute,
)


# -----------------------------------------
# train schedule create process
# -----------------------------------------

@feature_control(
    {
        "name": "v1.admin.master_data.train_schedules.create",
        "logging": {
            "console": True,
            "file": True,
        },
        "rate_limit": {
            "limit": 30,
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
    
    admin_user_id = int(admin_user_details.get("sub"))

    user_rate_key = f"ratelimit:v1.admin.master_data.schedules.create:user:{admin_user_id}"
    allowed = await rate_limiter.check_window_limit(
        key=user_rate_key,
        limit=settings.MASTERDATA_SCHEDULE_CREATE_USER_RATE_LIMIT,
        window=settings.MASTERDATA_SCHEDULE_CREATE_USER_RATE_WINDOW_SECONDS,
    )
    if not allowed:
        raise BaseAppException(
            status_code=429,
            messages=["Too many schedule create requests for this admin. Please try again later."],
        )

    result = await service.create_train_schedule(
        train_id=body.train_id,
        departure_date=body.departure_date,
        admin_user_id=admin_user_id,
        correlation_id=request.headers.get("x-correlation-id"),
        request_id=request.headers.get("x-request-id"),
    )

    return success_response(
        status_code=201,
        messages=["Schedule created successfully"],
        data=result,
    )

router.add_api_route(
    "/train-schedules",
    create_train_schedule,
    methods=["POST"],
    route_class_override=FeatureAPIRoute,
)