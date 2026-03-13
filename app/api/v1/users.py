"""
Users API v1
"""

from fastapi import APIRouter, Depends
from app.core.routing.feature_route import FeatureAPIRoute
from app.common.decorators.feature_control import feature_control
from app.core.response import success_response
from app.domains.users.schemas import UserSignupRequest
from app.domains.users.service import UsersService
from app.dependencies.users import get_users_service
from app.domains.users.service import UsersService


router = APIRouter()


# =========================================================
# Signup API
# =========================================================

@router.post(
    "/signup",
    route_class=FeatureAPIRoute,
)
@feature_control(
    {
        "name": "v1.users.signup",
        "logging": True,
        "rate_limit": {
            "limit": 10,
            "window": 3600,
        },
    }
)
async def signup_user(
    body: UserSignupRequest,
    service: UsersService = Depends(
        get_users_service
    ),
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
            "id": user.id,
            "email": user.email,
        },
    )