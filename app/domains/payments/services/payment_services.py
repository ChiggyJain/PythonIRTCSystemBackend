
from datetime import date, datetime, timedelta
import json
import httpx
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import BaseAppException
from app.core.response import (
    standardize_response, 
)
from app.core.settings import get_settings
from app.common.utils.datetime import now_ist, today_ist
from app.common.utils.orm_to_dict import orm_to_dict
from app.common.repository.idempotency.sqlalchemy_repo import IdempotencySQLAlchemyRepository
from app.domains.payments.repository.sqlalchemy_repo import PaymentSQLAlchemyRepository
from app.infrastructure.payment_gateway.payment_gateway_factory import PaymentGatewayFactory



settings = get_settings()



class PaymentService:

    def __init__(self, db_session: AsyncSession):
        self._db_session = db_session
        self.idempotency_repo = IdempotencySQLAlchemyRepository(db_session)
        self.payment_repo = PaymentSQLAlchemyRepository(db_session)
        


    async def create_payment_order_details(self, *, payload: dict) -> dict:
        
        try:

            # extracted parameters
            idempotency_key = payload.get("idempotency_key", "")
            user_id = int(payload.get("user_id", 0))
            booking_id = int(payload.get("booking_id", 0))
            amount = payload.get("amount", 0)
            currency = "INR"

            # fetching payment gateway instances details
            params1 = {
                "payment_gateway_service_provider": settings.payment_gateway_service_provider
            }
            payment_gateway_class_instances_obj = PaymentGatewayFactory.getPaymentGatewayInstances(**params1)

            # creating payment order request on selected payment gateway instances
            params2 = {
                "amount": amount,
                "currency" : "INR",
                # this is our Unique-ID which we sending to payment-gateway for order creating request
                # this is from booking-table primary key right now
                "receipt" : booking_id,
                # this is additional json information which we sending to payment-gateway for order creating request
                "notes" : {
                    "booking_id" : booking_id,
                    "user_id" : user_id
                }
            }
            payment_gateway_created_order_rsp_obj = payment_gateway_class_instances_obj.createOrder(**params2)
            
            # failed due to some reasons
            if payment_gateway_created_order_rsp_obj["status_code"]!=201:
                pass
            
            # successfully created
            if payment_gateway_created_order_rsp_obj["status_code"] == 201:
                
                # creating payment orders into table
                self.payment_repo.create_payment_orders(
                    idempotency_key=idempotency_key,
                    booking_id=booking_id,
                    user_id=user_id,
                    total_amount=amount,
                    currency=currency,
                    gateway_provider=settings.payment_gateway_service_provider,
                    gateway_order_id=payment_gateway_created_order_rsp_obj["payment_gateway_order_id"],
                    gateway_payment_id=None,
                    gateway_signature=None,
                    failure_reason=None,
                    metadata_json=None,
                    version=0,
                    status="CREATED"
                )

                # creating payment audit logs into table



        except Exception as e:

            pass