
from aiohttp import payload
from fastapi import (
    APIRouter, Depends, Request
)
from app.core.routing.feature_route import FeatureAPIRoute
from app.common.decorators.feature_control import feature_control
from app.core.response import success_response
from app.dependencies.auth import (
    get_auth_service, 
    get_token_service,
)
from app.domains.auth.services.auth_services import AuthService
from app.domains.auth.services.token_services import TokenService
from app.domains.auth.schemas.schemas import (
    RefreshTokenRequest,
    LogoutRequest,
)
from app.core.exceptions import BaseAppException
from app.common.security.token_decoder import(
    get_current_user_details_from_access_token,
    get_current_user_details_from_refresh_token
)
from app.common.cache.redis_cache import (
    build_cache_key,
    cache_delete,
    build_cache_set_key,
    cache_set_remove
)


router = APIRouter()



@feature_control(
    {
        "name": "user:refreshtoken",
        "logging": {
            "console" : True,
            "file" : True,
        },
        "rate_limit": {
            "limit": 200000,
            "window": 60,
        },
    }
)
async def refresh_token(
    body: RefreshTokenRequest,
    request: Request,
    auth_service: AuthService = Depends(
        get_auth_service
    ),
):

    payload = body.model_dump()
    payload["ip_address"] = request.client.host if request.client else None
    payload["user_agent"] = request.headers.get("user-agent")
    return await auth_service.rotate_tokens_by_refresh(payload=payload)


router.add_api_route(
    "/refresh",
    refresh_token,
    methods=["POST"],
    route_class_override=FeatureAPIRoute,
)


@feature_control(
    {
        "name": "user:logout:currentdevices",
        "logging": {
            "console" : True,
            "file" : True,
        },
        "rate_limit": {
            "limit": 200000,
            "window": 60,
        },
    }
)
async def logout(
    body: LogoutRequest,
    user_details_from_access_token: dict = Depends(get_current_user_details_from_access_token),
    auth_service: AuthService = Depends(
        get_auth_service
    ),
):
 
    return await auth_service.logout_by_token_pair(
        payload=body.model_dump(), 
        user_details_from_access_token=user_details_from_access_token
    )

router.add_api_route(
    "/logout",
    logout,
    methods=["POST"],
    route_class_override=FeatureAPIRoute,
)

@feature_control(
    {
        "name": "user:logout:alldevices",
        "logging": {
            "console" : True,
            "file" : True,
        },
        "rate_limit": {
            "limit": 200000,
            "window": 60,
        },
    }
)
async def logout_all_devices(
    body: LogoutRequest,
    user_details_from_access_token: dict = Depends(get_current_user_details_from_access_token),
    auth_service: AuthService = Depends(
        get_auth_service
    )
):

    return await auth_service.logout_from_all_devices_by_user_id(
        payload=body.model_dump(), 
        user_details_from_access_token=user_details_from_access_token
    )

router.add_api_route(
    "/logout-all-devices",
    logout_all_devices,
    methods=["POST"],
    route_class_override=FeatureAPIRoute,
)



