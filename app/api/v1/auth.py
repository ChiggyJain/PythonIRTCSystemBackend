
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
)
from app.common.security.jwt import decode_token


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
        raise Exception(
            "Invalid refresh token"
        )
    
    if payload.get("type") != "refresh":
        raise Exception(
            "Invalid token type"
        )
    
    token_id = payload.get("tid")
    token_row = await token_service.get_refresh(token_id)

    if not token_row:
        raise Exception(
            "Refresh token not found"
        )
    
    if token_row.revoked:
        raise Exception(
            "Refresh token revoked"
        )

    tokens = await token_service.create_tokens(
        user_id=int(payload["sub"])
    )

    return success_response(
        messages=["Token refreshed"],
        data=tokens,
    )


router.add_api_route(
    "/refresh",
    refresh_token,
    methods=["POST"],
    route_class_override=FeatureAPIRoute,
)