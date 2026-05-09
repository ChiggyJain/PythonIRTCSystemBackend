
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
from app.domains.auth.services.token_services import TokenService
from app.domains.auth.schemas.schemas import (
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
            "limit": 200000,
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

    # Decode refresh token payload
    user_details_from_refresh_token = await get_current_user_details_from_refresh_token(body.refresh_token)

    user_profile = user_details_from_refresh_token.get("profile", "User")
    user_id = int(user_details_from_refresh_token.get("sub"))
    access_token_id = int(user_details_from_refresh_token.get("against_token_id"))
    refresh_token_id = int(user_details_from_refresh_token.get("jti"))

    refresh_token_row = await token_service.get_refresh(refresh_token_id)
    if not refresh_token_row:
        raise BaseAppException(
            status_code=401,
            messages=["Refresh token not found"]
        )

    # DB-level type safety check
    if refresh_token_row.token_type != "refresh":
        raise BaseAppException(
            status_code=401,
            messages=["Invalid refresh token type"],
        )

    # DB-level ownership safety check
    if int(refresh_token_row.user_id) != user_id:
        raise BaseAppException(
            status_code=401,
            messages=["Refresh token user mismatch"],
        )

    if refresh_token_row.revoked:
        raise BaseAppException(
            status_code=401,
            messages=["Refresh token already revoked"]
        )

    if not token_service.is_raw_token_matches_stored_hash(
        raw_token=body.refresh_token,
        stored_hash=refresh_token_row.token_hash,
    ):
        raise BaseAppException(
            status_code=401,
            messages=["Invalid refresh token"],
        )

    # Optional linked access token type sanity check (if row still active)
    access_token_row = await token_service.get_access(access_token_id)
    if access_token_row and access_token_row.token_type != "access":
        raise BaseAppException(
            status_code=401,
            messages=["Invalid linked access token type"],
        )

    # Single flow: revoke old pair + issue new pair + cache cleanup
    tokens = await token_service.rotate_tokens_by_refresh(
        user_id=user_id,
        user_profile=user_profile,
        current_access_token_id=access_token_id,
        current_refresh_token_id=refresh_token_id,
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


@feature_control(
    {
        "name": "v1.auth.logout",
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
    auth_service: TokenService = Depends(
        get_auth_service
    ),
):
 
    return await auth_service.logout_by_token_pair(
        payload=body.model_dump(), 
        user_details_from_access_token=user_details_from_access_token
    )


    

    

    

    

    

    

    return success_response(
        messages=["Logout successful from current active device session"],
    )


router.add_api_route(
    "/logout",
    logout,
    methods=["POST"],
    route_class_override=FeatureAPIRoute,
)


# ---------------------------
# logout all devices process
# ---------------------------

@feature_control(
    {
        "name": "v1.auth.logout",
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
    token_service: TokenService = Depends(
        get_token_service
    ),
):

    # Decode refresh token payload
    user_details_from_refresh_token = await get_current_user_details_from_refresh_token(body.refresh_token)

    # Extract and normalize ids
    access_user_id = int(user_details_from_access_token.get("sub"))
    access_token_id = int(user_details_from_access_token.get("jti"))

    refresh_user_id = int(user_details_from_refresh_token.get("sub"))
    refresh_token_id = int(user_details_from_refresh_token.get("jti"))
    refresh_against_access_id = int(user_details_from_refresh_token.get("against_token_id"))

    # Token pair binding checks
    if access_user_id != refresh_user_id:
        raise BaseAppException(
            messages=["Access and refresh token user mismatch"],
            status_code=401,
        )

    if access_token_id != refresh_against_access_id:
        raise BaseAppException(
            messages=["Access and refresh token pair mismatch"],
            status_code=401,
        )

    # Access row validations
    access_token_row = await token_service.get_access(access_token_id)
    if not access_token_row:
        raise BaseAppException(
            messages=["Access token not found"],
            status_code=401,
        )

    if access_token_row.token_type != "access":
        raise BaseAppException(
            messages=["Invalid access token type"],
            status_code=401,
        )

    if int(access_token_row.user_id) != access_user_id:
        raise BaseAppException(
            messages=["Access token user mismatch"],
            status_code=401,
        )

    # Refresh row validations
    refresh_token_row = await token_service.get_refresh(refresh_token_id)
    if not refresh_token_row:
        raise BaseAppException(
            messages=["Refresh token not found"],
            status_code=401,
        )

    if refresh_token_row.token_type != "refresh":
        raise BaseAppException(
            messages=["Invalid refresh token type"],
            status_code=401,
        )

    if int(refresh_token_row.user_id) != refresh_user_id:
        raise BaseAppException(
            messages=["Refresh token user mismatch"],
            status_code=401,
        )

    if refresh_token_row.revoked:
        raise BaseAppException(
            messages=["Refresh token already revoked"],
            status_code=401,
        )

    if not token_service.is_raw_token_matches_stored_hash(
        raw_token=body.refresh_token,
        stored_hash=refresh_token_row.token_hash,
    ):
        raise BaseAppException(
            status_code=401,
            messages=["Invalid refresh token"],
        )

    # Single transaction revoke all (access-token, refresh-token) + best-effort cache cleanup
    await token_service.logout_from_all_devices_by_user_id(
        user_id=access_user_id,
    )

    return success_response(
        messages=["Logout successful from all active devices session"],
    )


router.add_api_route(
    "/logout-all-devices",
    logout_all_devices,
    methods=["POST"],
    route_class_override=FeatureAPIRoute,
)



