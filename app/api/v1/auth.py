
from fastapi import (
    APIRouter, Depends
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
    token_service: TokenService = Depends(
        get_token_service
    ),
):

    # decode refresh token
    payload = decode_token(body.refresh_token)

    if not payload:
        raise BaseAppException(
            status_code=401,
            messages=["Invalid refresh token"]
        )
    
    if payload.get("type") != "refresh":
        raise BaseAppException(
            status_code=401,
            messages=["Invalid refresh token type"]
        )
    
    token_id = payload.get("tid")
    token_row = await token_service.get_refresh(token_id)
    
    if not token_row:
        raise BaseAppException(
            status_code=401,
            messages=["Refresh token not found"]
        )
    
    if token_row.revoked:
        raise BaseAppException(
            status_code=401,
            messages=["Refresh token not revoked"]
        )

    await token_service.revoke(token_id=token_id)

    tokens = await token_service.create_tokens(
        user_id=int(payload["sub"])
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
    token_service: TokenService = Depends(
        get_token_service
    ),
):

    # decode the refresh token
    payload = decode_token(
        body.refresh_token
    )

    if not payload:
        raise BaseAppException(
            messages=["Invalid refresh token"],
            status_code=401,
        )

    if payload.get("type") != "refresh":
        raise BaseAppException(
            messages=["Invalid refresh token type"],
            status_code=401,
        )

    token_id = payload.get("tid")
    token_row = await token_service.get_refresh(
        token_id
    )

    if not token_row:
        raise BaseAppException(
            messages=["Refresh token not found"],
            status_code=401,
        )

    if token_row.revoked:
        raise BaseAppException(
            messages=["Refresh token already revoked"],
            status_code=401,
        )

    await token_service.revoke(
        token_id
    )

    return success_response(
        messages=["Logout successful"],
    )

router.add_api_route(
    "/logout",
    logout,
    methods=["POST"],
    route_class_override=FeatureAPIRoute,
)