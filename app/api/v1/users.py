
from fastapi import (
    APIRouter, Depends, Request
)
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
from app.dependencies.auth import (
    get_current_user_id_from_access_token,
    get_current_user_details_from_access_token
)
from app.dependencies.security import get_password_change_otp_service
from app.domains.security.service import (
    PasswordChangeOtpService,
)
from app.dependencies.security import get_email_verification_otp_service
from app.domains.security.emailverification_service import (
    EmailVerificationOtpService,
)
from app.dependencies.security import get_email_changed_otp_service
from app.domains.security.emailchanged_service import EmailChangedOtpService
from app.domains.security.schemas import (
    EmailChangeRequestOtpRequest,
    EmailChangeConfirmOtpRequest,
)
from app.domains.security.schemas import (
    PasswordChangeRequestOtpRequest,
    PasswordChangeConfirmRequest,
    EmailVerificationRequestOtpRequest,
    EmailVerificationConfirmOtpRequest,
)


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
            # "limit": 1000,
            # "window": 3600,
            "limit": 200000,
            "window": 60,
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
            # "limit": 5,
            # "window": 60,
            "limit": 200000,
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

    # validate user
    user = await service.login_user(email=body.email, password=body.password)
    
    # create tokens
    tokens = await token_service.create_tokens(
        user_id=user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return success_response(
        messages=["Login successful"],
        data={
            "tokens" : tokens
        },
    )

router.add_api_route(
    "/login",
    login_user,
    methods=["POST"],
    route_class_override=FeatureAPIRoute,
)


# -----------------------------
# user profile details process
# -----------------------------

@feature_control(
    {
        "name": "v1.users.profile_details",
        "logging": {
            "console": True,
            "file": True,
        },
        "rate_limit": {
            "limit": 200000,
            "window": 60,
        },
    }
)
async def profile_details(
    user_details_from_access_token: dict = Depends(
        get_current_user_details_from_access_token
    ),
    service: UsersService = Depends(
        get_users_service
    ),
):
    
    user_id = user_details_from_access_token.get("sub")
    user_profile_details = await service.get_profile_details(user_id=user_id)
    
    return success_response(
        messages=["User profile details found successfully"],
        data=user_profile_details,
    )

router.add_api_route(
    "/profile_details",
    profile_details,
    methods=["GET"],
    route_class_override=FeatureAPIRoute,
)




# ---------------------------------
# password change request otp
# ---------------------------------

@feature_control(
    {
        "name": "v1.users.password_change_request_otp",
        "logging": {
            "console": True,
            "file": True,
        },
        "rate_limit": {
            "limit": 200000,
            "window": 60,
        },
    }
)
async def password_change_request_otp(
    body: PasswordChangeRequestOtpRequest,
    request: Request,
    user_id_from_access_token: int = Depends(get_current_user_id_from_access_token),
    service: PasswordChangeOtpService = Depends(get_password_change_otp_service),
):
    
    result = await service.request_password_change_otp(
        user_id=user_id_from_access_token,
        channel=body.channel,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        correlation_id=request.headers.get("x-correlation-id"),
        request_id=request.headers.get("x-request-id"),
    )

    return success_response(
        status_code=202,
        messages=["OTP request accepted"],
        data=result,
    )


router.add_api_route(
    "/password/change/request-otp",
    password_change_request_otp,
    methods=["POST"],
    route_class_override=FeatureAPIRoute,
)


# ---------------------------------
# password change confirm
# ---------------------------------

@feature_control(
    {
        "name": "v1.users.password_change_confirm",
        "logging": {
            "console": True,
            "file": True,
        },
        "rate_limit": {
            "limit": 10,
            "window": 60,
        },
    }
)
async def password_change_confirm(
    body: PasswordChangeConfirmRequest,
    request: Request,
    user_id_from_access_token: int = Depends(get_current_user_id_from_access_token),
    service: PasswordChangeOtpService = Depends(get_password_change_otp_service),
):
    
    result = await service.confirm_password_change(
        user_id=user_id_from_access_token,
        challenge_id=body.challenge_id,
        otp=body.otp,
        new_password=body.new_password,
        confirm_password=body.confirm_password,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        correlation_id=request.headers.get("x-correlation-id"),
        request_id=request.headers.get("x-request-id"),
    )

    return success_response(
        messages=["Password changed successfully"],
        data=result,
    )


router.add_api_route(
    "/password/change/confirm",
    password_change_confirm,
    methods=["POST"],
    route_class_override=FeatureAPIRoute,
)



# ---------------------------------
# email verification request otp
# ---------------------------------

@feature_control(
    {
        "name": "v1.users.email_verification_request_otp",
        "logging": {
            "console": True, 
            "file": True
        },
        "rate_limit": {
            "limit": 10, 
            "window": 60
        },
    }
)
async def email_verification_request_otp(
    body: EmailVerificationRequestOtpRequest,
    request: Request,
    user_id_from_access_token: int = Depends(get_current_user_id_from_access_token),
    service: EmailVerificationOtpService = Depends(get_email_verification_otp_service),
):
    
    result = await service.request_email_verification_otp(
        user_id=user_id_from_access_token,
        channel=body.channel,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        correlation_id=request.headers.get("x-correlation-id"),
        request_id=request.headers.get("x-request-id"),
    )

    return success_response(
        status_code=202,
        messages=["Email verification OTP request accepted"],
        data=result,
    )


router.add_api_route(
    "/email/verification/request-otp",
    email_verification_request_otp,
    methods=["POST"],
    route_class_override=FeatureAPIRoute,
)


# ---------------------------------
# email verification confirm otp
# ---------------------------------

@feature_control(
    {
        "name": "v1.users.email_verification_confirm",
        "logging": {
            "console": True, 
            "file": True
        },
        "rate_limit": {
            "limit": 10, 
            "window": 60
        },
    }
)
async def email_verification_confirm_otp(
    body: EmailVerificationConfirmOtpRequest,
    request: Request,
    user_id_from_access_token: int = Depends(get_current_user_id_from_access_token),
    service: EmailVerificationOtpService = Depends(get_email_verification_otp_service),
):
    
    result = await service.confirm_email_verification_otp(
        user_id=user_id_from_access_token,
        challenge_id=body.challenge_id,
        otp=body.otp,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        correlation_id=request.headers.get("x-correlation-id"),
        request_id=request.headers.get("x-request-id"),
    )

    return success_response(
        messages=["Email verified successfully"],
        data=result,
    )


router.add_api_route(
    "/email/verification/confirm",
    email_verification_confirm_otp,
    methods=["POST"],
    route_class_override=FeatureAPIRoute,
)



# ---------------------------------
# email change otp request
# ---------------------------------

@feature_control(
    {
        "name": "v1.users.email_change_request_otp",
        "logging": {""
            "console": True, 
            "file": True
        },
        "rate_limit": {
            "limit": 10, 
            "window": 60
        },
    }
)
async def email_change_request_otp(
    body: EmailChangeRequestOtpRequest,
    request: Request,
    user_id_fron_access_token: int = Depends(get_current_user_id_from_access_token),
    service: EmailChangedOtpService = Depends(get_email_changed_otp_service),
):
    
    result = await service.request_email_change_otp(
        user_id=user_id_fron_access_token,
        channel=body.channel,
        new_email=str(body.new_email),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        correlation_id=request.headers.get("x-correlation-id"),
        request_id=request.headers.get("x-request-id"),
    )
    return success_response(
        status_code=202,
        messages=["Email change OTP request accepted"],
        data=result,
    )


router.add_api_route(
    "/email/change/request-otp",
    email_change_request_otp,
    methods=["POST"],
    route_class_override=FeatureAPIRoute,
)



# ---------------------------------
# email change otp confirmation
# ---------------------------------


@feature_control(
    {
        "name": "v1.users.email_change_confirm",
        "logging": {
            "console": True, 
            "file": True
        },
        "rate_limit": {
            "limit": 10, 
            "window": 60
        },
    }
)
async def email_change_confirm_otp(
    body: EmailChangeConfirmOtpRequest,
    request: Request,
    user_id_fron_access_token: int = Depends(get_current_user_id_from_access_token),
    service: EmailChangedOtpService = Depends(get_email_changed_otp_service),
):
    
    result = await service.confirm_email_change_otp(
        user_id=user_id_fron_access_token,
        challenge_id=body.challenge_id,
        otp=body.otp,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        correlation_id=request.headers.get("x-correlation-id"),
        request_id=request.headers.get("x-request-id"),
    )
    return success_response(
        messages=["Email changed successfully"],
        data=result,
    )


router.add_api_route(
    "/email/change/confirm",
    email_change_confirm_otp,
    methods=["POST"],
    route_class_override=FeatureAPIRoute,
)
