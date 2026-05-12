
from fastapi import APIRouter, Depends, Request
from app.common.decorators.feature_control import feature_control
from app.core.routing.feature_route import FeatureAPIRoute
from app.core.settings import get_settings
from app.common.security.token_decoder import(
    get_current_user_id_from_access_token,
    get_current_user_details_from_access_token
)
from app.domains.booking.schemas.bookings_schemas import CreateBookingRequest
from app.domains.booking.schemas.bookings_schemas import VerifyPaymentRequest
from app.domains.booking.services.booking_services import BookingService
from app.dependencies.bookings import get_booking_service


settings = get_settings()
router = APIRouter()


@feature_control(
    {
        "name": "user:booking:create",
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
async def create_booking(
    body: CreateBookingRequest,
    request: Request,
    user_details_from_access_token: dict = Depends(get_current_user_details_from_access_token),
    service: BookingService = Depends(get_booking_service),
):
    
    payload = body.model_dump()
    payload["user_id"] = int(user_details_from_access_token.get("sub"))
    payload["ip_address"] = request.client.host if request.client else None
    payload["user-agent"] = request.headers.get("user-agent")
    payload["correlation_id"] = request.headers.get("x-correlation-id")
    payload["request_id"] = request.headers.get("x-request-id")
    return await service.create_booking_details(payload=payload)

router.add_api_route(
    "/",
    create_booking,
    methods=["POST"],
    route_class_override=FeatureAPIRoute,
)


@feature_control(
    {
        "name": "user:booking:create",
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
async def verify_payment(
    body: VerifyPaymentRequest,
    request: Request,
    user_details_from_access_token: dict = Depends(get_current_user_details_from_access_token),
    service: BookingService = Depends(get_booking_service),
):
    
    payload = body.model_dump()
    payload["user_id"] = int(user_details_from_access_token.get("sub"))
    payload["ip_address"] = request.client.host if request.client else None
    payload["user-agent"] = request.headers.get("user-agent")
    payload["correlation_id"] = request.headers.get("x-correlation-id")
    payload["request_id"] = request.headers.get("x-request-id")
    return await service.verify_payment_details(payload=payload)

router.add_api_route(
    "/verify-payment",
    verify_payment,
    methods=["POST"],
    route_class_override=FeatureAPIRoute,
)



