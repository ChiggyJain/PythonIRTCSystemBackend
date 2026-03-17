
from fastapi import (
    APIRouter, Depends, Request
)
from app.core.routing.feature_route import FeatureAPIRoute
from app.common.decorators.feature_control import feature_control
from app.core.response import success_response
from app.dependencies.auth import get_token_service
from app.domains.auth.service import TokenService
from app.domains.auth.schemas import (
    RefreshTokenRequest,
    LogoutRequest,
)
from app.common.security.jwt import decode_token
from app.core.exceptions import BaseAppException
from app.dependencies.auth import (
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


# -------------------------
# refresh token process
# -------------------------

@feature_control(
    {
        "name": "v1.auth.refresh",
        "logging": {
            "console" : True,
            "file" : True,
        },
        "rate_limit": {
            "limit": 10,
            "window": 60,
        },
    }
)
async def refresh_token(
    body: RefreshTokenRequest,
    request: Request,
    token_service: TokenService = Depends(
        get_token_service
    ),
):

    # decoding user-details from refresh token
    user_details_from_refresh_token = await get_current_user_details_from_refresh_token(body.refresh_token)

    access_token_id = user_details_from_refresh_token.get("against_token_id")
    refresh_token_id = user_details_from_refresh_token.get("jti")
    refresh_token_row = await token_service.get_refresh(refresh_token_id)
    if not refresh_token_row:
        raise BaseAppException(
            status_code=401,
            messages=["Refresh token not found"]
        )
    if refresh_token_row.revoked:
        raise BaseAppException(
            status_code=401,
            messages=["Refresh token not revoked"]
        )

    # revoke refresh token from table
    await token_service.revoke(token_id=refresh_token_id)

    # revoke access token from table
    await token_service.revoke(token_id=access_token_id)

    # remove keys from cache 
    cacheKey = build_cache_key(f"auth:access:jti:{access_token_id}")
    await cache_delete(cacheKey)

    # creating new access and refresh token
    tokens = await token_service.create_tokens(
        user_id=int(user_details_from_refresh_token.get("sub")),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return success_response(
        messages=["Token refreshed successfully"],
        data=tokens,
    )


router.add_api_route(
    "/refresh",
    refresh_token,
    methods=["POST"],
    route_class_override=FeatureAPIRoute,
)



# -------------------------
# logout process
# -------------------------


@feature_control(
    {
        "name": "v1.auth.logout",
        "logging": {
            "console" : True,
            "file" : True,
        },
        "rate_limit": {
            "limit": 20,
            "window": 60,
        },
    }
)
async def logout(
    body: LogoutRequest,
    user_details_from_access_token: dict = Depends(get_current_user_details_from_access_token),
    token_service: TokenService = Depends(
        get_token_service
    ),
):

    # extracting refresh token
    user_details_from_refresh_token = await get_current_user_details_from_refresh_token(body.refresh_token)
    
    # handle case for access token
    access_token_id = user_details_from_access_token.get("jti")
    access_token_row = await token_service.get_access(access_token_id)
    if not access_token_row:
        raise BaseAppException(
            messages=["Access token not found"],
            status_code=401,
        )
    await token_service.revoke(access_token_id)

    # remove keys from cache 
    cacheKey = build_cache_key(f"auth:access:jti:{access_token_id}")
    await cache_delete(cacheKey)
    user_id = user_details_from_access_token.get("sub")
    cacheKey = build_cache_set_key(f"auth:user:access:index:{user_id}")
    await cache_set_remove(cacheKey, access_token_id)

    # handle case for refresh token
    refresh_token_id = user_details_from_refresh_token.get("jti")
    refresh_token_row = await token_service.get_refresh(refresh_token_id)
    if not refresh_token_row:
        raise BaseAppException(
            messages=["Refresh token not found"],
            status_code=401,
        )
    if refresh_token_row.revoked:
        raise BaseAppException(
            messages=["Refresh token already revoked"],
            status_code=401,
        )
    await token_service.revoke(refresh_token_id)

    return success_response(
        messages=["Logout successful"],
    )

router.add_api_route(
    "/logout",
    logout,
    methods=["POST"],
    route_class_override=FeatureAPIRoute,
)