
from fastapi import APIRouter, Depends, Request
from app.common.decorators.feature_control import feature_control
from app.core.routing.feature_route import FeatureAPIRoute
from app.core.settings import get_settings
from app.common.security.token_decoder import(
    get_current_user_id_from_access_token,
    get_current_user_details_from_access_token
)
from app.domains.payments.schemas.payments_schemas import CreatePaymentOrderRequest
from app.domains.payments.schemas.payments_schemas import CreatePaymentOrderRefundRequest
from app.domains.payments.services.payment_services import PaymentService
from app.dependencies.payments import get_payment_service


settings = get_settings()
router = APIRouter()


@feature_control(
    {
        "name": "user:payment:order:create",
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
async def create_payment_order(
    body: CreatePaymentOrderRequest,
    request: Request,
    service: PaymentService = Depends(get_payment_service),
):
    
    payload = body.model_dump()
    payload["ip_address"] = request.client.host if request.client else None
    payload["user-agent"] = request.headers.get("user-agent")
    payload["correlation_id"] = request.headers.get("x-correlation-id")
    payload["request_id"] = request.headers.get("x-request-id")
    return await service.create_payment_order_details(payload=payload)

router.add_api_route(
    "/orders",
    create_payment_order,
    methods=["POST"],
    route_class_override=FeatureAPIRoute,
)


@feature_control(
    {
        "name": "user:payment:order:refund",
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
async def create_payment_order_refund(
    body: CreatePaymentOrderRefundRequest,
    request: Request,
    service: PaymentService = Depends(get_payment_service),
):
    
    payload = body.model_dump()
    payload["ip_address"] = request.client.host if request.client else None
    payload["user-agent"] = request.headers.get("user-agent")
    payload["correlation_id"] = request.headers.get("x-correlation-id")
    payload["request_id"] = request.headers.get("x-request-id")
    return await service.create_payment_order_refund_details(payload=payload)

router.add_api_route(
    "/refunds",
    create_payment_order_refund,
    methods=["POST"],
    route_class_override=FeatureAPIRoute,
)



