
from fastapi import (
    APIRouter, Depends, Request
)
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.routing.feature_route import FeatureAPIRoute
from app.common.decorators.feature_control import feature_control
from app.core.response import success_response
from app.domains.users.schemas import (
    UserSignupRequest, 
    UserLoginRequest
)
from app.domains.users.service import UsersService
from app.dependencies.users import get_users_service
from app.dependencies.auth import get_token_service
from app.domains.auth.service import TokenService



router = APIRouter()


# -------------------------
# user signup process
# -------------------------

@feature_control(
    {
        "name": "v1.users.signup",
        "logging": {
            "console" : True,
            "file" : False
        },
        "rate_limit": {
            "limit": 1000,
            "window": 3600,
        },
    }
)
async def signup_user(
    body: UserSignupRequest,
    service: UsersService = Depends(get_users_service),
):

    user = await service.signup_user(
        first_name=body.first_name,
        last_name=body.last_name,
        mobile=body.mobile,
        email=body.email,
        password=body.password,
        gender=body.gender,
    )

    return success_response(
        messages=["User created successfully"],
        data={
            "userId": user.id,
            "userEmail": user.email,
        },
    )


router.add_api_route(
    "/signup",
    signup_user,
    methods=["POST"],
    route_class_override=FeatureAPIRoute,
)


# -------------------------
# user login process
# -------------------------

@feature_control(
    {
        "name": "v1.users.login",
        "logging": {
            "console": True,
            "file": True,
        },
        "rate_limit": {
            "limit": 5,
            "window": 60,
        },
    }
)
async def login_user(
    body: UserLoginRequest,
    request: Request,
    service: UsersService = Depends(
        get_users_service
    ),
    token_service: TokenService = Depends(
        get_token_service
    ),
):

    # -------------------------
    # validate user
    # -------------------------

    user = await service.login_user(
        email=body.email,
        password=body.password,
    )

    # -------------------------
    # create tokens
    # -------------------------

    tokens = await token_service.create_tokens(
        user_id=user.id,
        ip_address=request.client.host
        if request.client
        else None,
        user_agent=request.headers.get(
            "user-agent"
        ),
    )

    return success_response(
        messages=["Login successful"],
        data={
            "userId": user.id,
            "userEmail": user.email,
            "userMobile" : user.mobile,
            "userGender" : user.gender,
            "tokens" : tokens
        },
    )

router.add_api_route(
    "/login",
    login_user,
    methods=["POST"],
    route_class_override=FeatureAPIRoute,
)

