
from fastapi import APIRouter, Depends, Request
from app.common.decorators.feature_control import feature_control
from app.common.utils.ratelimiter import rate_limiter
from app.core.exceptions import BaseAppException
from app.core.response import success_response
from app.core.routing.feature_route import FeatureAPIRoute
from app.core.settings import get_settings



settings = get_settings()
router = APIRouter()


# -------------------------
# stations create process
# -------------------------

@feature_control(
    {
        "name": "v1.inventory.schedules.schedule_id.availability",
        "logging": {
            "console": True,
            "file": True,
        },
        "rate_limit": {
            "limit": 1000,
            "window": 60,
        },
    }
)
async def inventory_schedules_availabiliity(    
    service: StationsService = Depends(get_stations_service),
):
    
    admin_user_id = int(admin_user_details.get("sub"))

    # user-level limiter
    user_rate_key = f"ratelimit:v1.admin.master_data.stations.create:user:{admin_user_id}"
    allowed = await rate_limiter.check_window_limit(
        key=user_rate_key,
        limit=settings.MASTERDATA_STATION_CREATE_USER_RATE_LIMIT,
        window=settings.MASTERDATA_STATION_CREATE_USER_RATE_WINDOW_SECONDS,
    )
    if not allowed:
        raise BaseAppException(
            status_code=429,
            messages=["Too many station create requests for this admin. Please try again later."],
        )

    result = await service.create_station(
        name=body.name,
        code=body.code,
        city=body.city,
        state=body.state,
        admin_user_id=admin_user_id,
        correlation_id=request.headers.get("x-correlation-id"),
        request_id=request.headers.get("x-request-id"),
    )

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


