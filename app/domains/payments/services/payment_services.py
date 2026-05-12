
from datetime import date, datetime, timedelta
import json
from dns import message
import httpx
from sqlalchemy import null
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import BaseAppException
from app.core.response import (
    standardize_response, 
)
from app.core.settings import get_settings
from app.common.utils.datetime import now_ist, today_ist
from app.common.utils.orm_to_dict import orm_to_dict
from app.domains.payments.models.payment_orders_models import PaymentOrders
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
            
            # checking given idempotency key exists or not
            event_key = idempotency_key
            existing_idempotency_record = await self.idempotency_repo.get_idempotency_record_by_event_key(event_key)
            if existing_idempotency_record:
                return standardize_response(
                    status_code=200,
                    messages=[f"payment orders already created successfully"],
                    data=existing_idempotency_record.event_response,
                )
            
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
            payment_gateway_created_order_rsp_obj = await payment_gateway_class_instances_obj.createOrder(**params2)
            
            # failed due to some reasons
            if payment_gateway_created_order_rsp_obj["status_code"]!=201:

                # storing idempotency-key details
                await self.idempotency_repo.add_idempotency_record(
                    event_key = event_key,
                    event_type = "payment_orders",
                    event_response = {
                        "status_code" : payment_gateway_created_order_rsp_obj["status_code"],
                        "messages" : payment_gateway_created_order_rsp_obj["messages"],
                        "payment_order_id" : "",
                        "gateway_provider" : "",
                        "gateway_provider_key_id" : "",
                        "gateway_order_id" : "",
                        "amount" : "",
                        "currency" : "",
                        "payment_order_status" : ""
                    }
                )

                await self._db_session.commit()
                
                return standardize_response(
                    status_code=500,
                    messages=payment_gateway_created_order_rsp_obj["messages"]
                )
            
            # successfully created
            if payment_gateway_created_order_rsp_obj["status_code"] == 201:
                
                # creating payment orders into table
                created_payment_orders_row = await self.payment_repo.create_payment_orders(
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
                created_payment_audit_logs_row = await self.payment_repo.create_payment_audit_logs(
                    payment_order_id=created_payment_orders_row.id,
                    action="ORDER_CREATED",
                    gateway_response=payment_gateway_created_order_rsp_obj["raw_response"],
                    metadata_json={
                        "user_id" : user_id,
                        "booking_id" : booking_id,
                        "amount" : amount,
                    },
                    status="A"
                )
                
                # storing idempotency-key details
                await self.idempotency_repo.add_idempotency_record(
                    event_key = event_key,
                    event_type = "payment_orders",
                    event_response = {
                        "status_code" : 201,
                        "messages" : ["Payment orders created successfully"],
                        "payment_order_id" : created_payment_orders_row.id,
                        "gateway_provider" : created_payment_orders_row.gateway_provider,
                        "gateway_provider_key_id" : "",
                        "gateway_order_id" : created_payment_orders_row.gateway_order_id,
                        "amount" : created_payment_orders_row.total_amount,
                        "currency" : created_payment_orders_row.currency,
                        "payment_order_status" : created_payment_orders_row.status
                    }
                )

                await self._db_session.commit()

                return standardize_response(
                    status_code=201,
                    messages=[f"Payment orders created successfully"],
                    data={
                        "payment_order_id" : created_payment_orders_row.id,
                        "gateway_provider" : created_payment_orders_row.gateway_provider,
                        "gateway_provider_key_id" : "",
                        "gateway_order_id" : created_payment_orders_row.gateway_order_id,
                        "amount" : created_payment_orders_row.total_amount,
                        "currency" : created_payment_orders_row.currency,
                        "payment_order_status" : created_payment_orders_row.status
                    }
                )
    
        except Exception as e:
            await self._db_session.rollback()
            return standardize_response(
                status_code=500,
                messages=[f"{str(e)}"]
            )



    async def create_payment_order_refund_details(self, *, payload: dict) -> dict:
        
        try:

            # extracted parameters
            idempotency_key = payload.get("idempotency_key", "")
            payment_order_id = int(payload.get("payment_order_id", 0))
            amount = payload.get("amount", 0)
            reason = payload.get("reason", "Unknown")
            
            # checking given idempotency key exists or not
            event_key = idempotency_key
            existing_idempotency_record = await self.idempotency_repo.get_idempotency_record_by_event_key(event_key)
            if existing_idempotency_record:
                return standardize_response(
                    status_code=200,
                    messages=[f"Payment refund request already inititated successfully"],
                    data=existing_idempotency_record.event_response,
                )

            # fetching payment order details
            payment_order_list = await self.payment_repo.get_payment_orders_details(
                where_conditions = [
                    PaymentOrders.id == payment_order_id,
                ],
                order_by = [
                    PaymentOrders.id.asc()
                ]
            )
            if not payment_order_list:
                return standardize_response(
                    status_code=404,
                    messages=[f"Payment order not found. No refund"]
                )
            if payment_order_list:
                payment_order = payment_order_list[0]
                if payment_order.status not in ["CAPTURED", "PARTIALLY_REFUNDED"]:
                    return standardize_response(
                        status_code=404,
                        messages=[f"Cannot refund the payment in {payment_order.status} status"]
                    )
                if payment_order.gateway_order_id in [None, null, ""]:
                    return standardize_response(
                        status_code=404,
                        messages=[f"Payment order request is not created on payment gateway service provider portal. No refund"]
                    )
                if payment_order.gateway_payment_id in [None, null, ""]:
                    return standardize_response(
                        status_code=404,
                        messages=[f"Payment gateway payment-id not found. No refund"]
                    )
                
                # fetching payment gateway instances details
                params1 = {
                    "payment_gateway_service_provider": payment_order.gateway_provider
                }
                payment_gateway_class_instances_obj = PaymentGatewayFactory.getPaymentGatewayInstances(**params1)
                
                # creating payment order refund request on selected payment gateway instances
                params2 = {
                    "gateway_payment_id" : payment_order.gateway_payment_id,
                    "amount": amount,
                    "notes" : {
                        "booking_id" : payment_order.booking_id,
                        "reason" : reason
                    }
                }
                payment_gateway_order_refund_rsp_obj = await payment_gateway_class_instances_obj.initiateRefund(**params2)
            
                if payment_gateway_order_refund_rsp_obj["status_code"]>0:
                    
                    payment_gateway_refund_rsp_obj_status_code = payment_gateway_order_refund_rsp_obj["status_code"]
                    
                    # creating refund orders into table
                    created_refund_orders_row = await self.payment_repo.create_refund_orders(
                        idempotency_key=idempotency_key,
                        payment_order_id=payment_order.id,
                        total_amount=amount,
                        reason=reason,
                        gateway_refund_id=payment_gateway_order_refund_rsp_obj["payment_gateway_refund_id"],
                        failure_reason=None,
                        metadata_json=None,
                        status="INITIATED" if payment_gateway_refund_rsp_obj_status_code == 201 else "FAILED",
                    )

                    # updating the payment order table status
                    if payment_gateway_refund_rsp_obj_status_code == 200:
                        cnt_of_payment_orders_row_updated = await self.payment_repo.update_payment_orders_details(
                            where_data = {
                                PaymentOrders.id == payment_order.id
                            },
                            update_data = {
                                "version" : PaymentOrders.version + 1,
                                "status" : "REFUND_INITIATED"
                            }
                        )

                    # creating payment audit logs into table
                    created_payment_audit_logs_row = await self.payment_repo.create_payment_audit_logs(
                        payment_order_id=payment_order.id,
                        action="REFUND_INITIATED",
                        gateway_response=payment_gateway_order_refund_rsp_obj["raw_response"],
                        metadata_json={
                            "refund_id" : payment_gateway_order_refund_rsp_obj["payment_gateway_refund_id"],
                            "amount" : amount,
                            "reason" : reason
                        },
                        status="A"
                    )
                    
                    # storing idempotency-key details
                    await self.idempotency_repo.add_idempotency_record(
                        event_key = event_key,
                        event_type = "refund_orders",
                        event_response = {
                            "payment_order_id" : payment_order.id,
                            "gateway_provider" : payment_order.gateway_provider,
                            "gateway_provider_key_id" : "",
                            "payment_refund_id" : created_refund_orders_row.id,
                            "gateway_refund_id" : payment_gateway_order_refund_rsp_obj["payment_gateway_refund_id"],
                            "amount" : payment_gateway_order_refund_rsp_obj["amount"],
                            "refund_status" : payment_gateway_order_refund_rsp_obj["status"]
                        }
                    )

                    await self._db_session.commit()

                    return standardize_response(
                        status_code=201,
                        messages=[f"Payment refund request inititated successfully"],
                        data={
                            "payment_order_id" : payment_order.id,
                            "gateway_provider" : payment_order.gateway_provider,
                            "gateway_provider_key_id" : "",
                            "payment_refund_id" : created_refund_orders_row.id,
                            "gateway_refund_id" : payment_gateway_order_refund_rsp_obj["payment_gateway_refund_id"],
                            "amount" : payment_gateway_order_refund_rsp_obj["amount"],
                            "refund_status" : payment_gateway_order_refund_rsp_obj["status"]
                        }
                    )

    
        except Exception as e:
            return standardize_response(
                status_code=500,
                messages=[f"{str(e)}"]
            )
            