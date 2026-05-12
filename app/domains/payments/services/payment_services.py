
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
from app.infrastructure.outbox.repository.sqlalchemy_repo import OutboxEventsSQLAlchemyRepository


settings = get_settings()



class PaymentService:

    def __init__(self, db_session: AsyncSession):
        self._db_session = db_session
        self.idempotency_repo = IdempotencySQLAlchemyRepository(db_session)
        self.payment_repo = PaymentSQLAlchemyRepository(db_session)
        self.outbox_repo = OutboxEventsSQLAlchemyRepository(db_session)


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
                "payment_gateway_service_provider": settings.PAYMENT_GATEWAY_SERVICE_PROVIDER
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
            if payment_gateway_created_order_rsp_obj["status_code"]>0:
                
                # creating payment orders into table
                created_payment_orders_row = await self.payment_repo.create_payment_orders(
                    idempotency_key=idempotency_key,
                    booking_id=booking_id,
                    user_id=user_id,
                    total_amount=amount,
                    currency=currency,
                    gateway_provider=settings.PAYMENT_GATEWAY_SERVICE_PROVIDER,
                    gateway_order_id=payment_gateway_created_order_rsp_obj["payment_gateway_order_id"],
                    gateway_payment_id=None,
                    gateway_signature=None,
                    failure_reason=None,
                    metadata_json=None,
                    version=0,
                    status="CREATED" if payment_gateway_created_order_rsp_obj["status_code"] == 201 else "FAILED",
                )

                # creating payment audit logs into table
                created_payment_audit_logs_row = await self.payment_repo.create_payment_audit_logs(
                    payment_order_id=created_payment_orders_row.id,
                    action="ORDER_CREATED",
                    gateway_response=payment_gateway_created_order_rsp_obj["raw_response"],
                    metadata_json={
                        "user_id" : user_id,
                        "booking_id" : booking_id,
                        "amount" : str(amount),
                    },
                    status="A"
                )
                
                # storing idempotency-key details
                await self.idempotency_repo.add_idempotency_record(
                    event_key = event_key,
                    event_type = "payment_orders",
                    event_response = {
                        "payment_order_id" : created_payment_orders_row.id,
                        "gateway_provider" : created_payment_orders_row.gateway_provider,
                        "gateway_provider_key_id" : "",
                        "gateway_order_id" : created_payment_orders_row.gateway_order_id,
                        "amount" : str(created_payment_orders_row.total_amount),
                        "currency" : created_payment_orders_row.currency,
                        "payment_order_status" : created_payment_orders_row.status
                    }
                )

                await self._db_session.commit()

                return standardize_response(
                    status_code=payment_gateway_created_order_rsp_obj["status_code"],
                    messages=payment_gateway_created_order_rsp_obj["messages"],
                    data={
                        "payment_order_id" : created_payment_orders_row.id,
                        "gateway_provider" : created_payment_orders_row.gateway_provider,
                        "gateway_provider_key_id" : "",
                        "gateway_order_id" : created_payment_orders_row.gateway_order_id,
                        "amount" : str(created_payment_orders_row.total_amount),
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



    async def create_payment_refund_details(self, *, payload: dict) -> dict:
        
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
                payment_gateway_refund_rsp_obj = await payment_gateway_class_instances_obj.initiateRefund(**params2)
                if payment_gateway_refund_rsp_obj["status_code"]>0:
                    
                    # creating refund orders into table
                    created_refund_orders_row = await self.payment_repo.create_refund_orders(
                        idempotency_key=idempotency_key,
                        payment_order_id=payment_order.id,
                        total_amount=amount,
                        reason=reason,
                        gateway_refund_id=payment_gateway_refund_rsp_obj["payment_gateway_refund_id"],
                        failure_reason=None,
                        metadata_json=None,
                        status="INITIATED" if payment_gateway_refund_rsp_obj["status_code"] == 201 else "FAILED",
                    )

                    # updating the payment order table status
                    if payment_gateway_refund_rsp_obj["status_code"] == 200:
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
                        gateway_response=payment_gateway_refund_rsp_obj["raw_response"],
                        metadata_json={
                            "refund_id" : payment_gateway_refund_rsp_obj["payment_gateway_refund_id"],
                            "amount" : str(amount),
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
                            "gateway_refund_id" : payment_gateway_refund_rsp_obj["payment_gateway_refund_id"],
                            "amount" : str(payment_gateway_refund_rsp_obj["amount"]),
                            "refund_status" : payment_gateway_refund_rsp_obj["status"]
                        }
                    )

                    await self._db_session.commit()
                    
                    return standardize_response(
                        status_code=payment_gateway_refund_rsp_obj["status_code"],
                        messages=payment_gateway_refund_rsp_obj["messages"],
                        data={
                            "payment_order_id" : payment_order.id,
                            "gateway_provider" : payment_order.gateway_provider,
                            "gateway_provider_key_id" : "",
                            "payment_refund_id" : created_refund_orders_row.id,
                            "gateway_refund_id" : payment_gateway_refund_rsp_obj["payment_gateway_refund_id"],
                            "amount" : str(payment_gateway_refund_rsp_obj["amount"]),
                            "refund_status" : payment_gateway_refund_rsp_obj["status"]
                        }
                    )

    
        except Exception as e:
            await self._db_session.rollback()
            return standardize_response(
                status_code=500,
                messages=[f"{str(e)}"]
            )



    async def verify_payment_details(self, *, payload: dict) -> dict:
        
        try:

            # extracted parameters
            payment_order_id = payload.get("payment_order_id", 0)
            gateway_payment_id = payload.get("gateway_payment_id", "")
            gateway_payment_signature = payload.get("gateway_payment_signature", "")
    
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
                    messages=[f"Payment order not found. No verification"]
                )
            if payment_order_list:

                payment_order = payment_order_list[0]
                if payment_order.status not in ["CREATED", "CAPTURED"]:
                    return standardize_response(
                        status_code=400,
                        messages=[f"Payment order is in {payment_order.status} status"],
                        data={
                            "booking_id" : payment_order.booking_id,
                            "payment_order_id" : payment_order.id,
                            "gateway_order_id" : payment_order.gateway_order_id,
                            "gateway_payment_id" : payment_order.gateway_payment_id,
                            "payment_order_status" : payment_order.status,
                        }
                    )
                if payment_order.status == "CAPTURED":
                    return standardize_response(
                        status_code=200,
                        messages=[f"Payment already captured"],
                        data={
                            "booking_id" : payment_order.booking_id,
                            "payment_order_id" : payment_order.id,
                            "gateway_order_id" : payment_order.gateway_order_id,
                            "gateway_payment_id" : payment_order.gateway_payment_id,
                            "payment_order_status" : "CAPTURED",
                        }
                    )
                
                # fetching payment gateway instances details
                params1 = {
                    "payment_gateway_service_provider": payment_order.gateway_provider
                }
                payment_gateway_class_instances_obj = PaymentGatewayFactory.getPaymentGatewayInstances(**params1)
                
                # verifying payment signature on selected payment gateway instances
                params2 = {
                    "gateway_order_id" : payment_order.gateway_order_id,
                    "gateway_payment_id": gateway_payment_id,
                    "gateway_payment_signature" : gateway_payment_signature,
                }
                payment_gateway_verify_rsp_obj = await payment_gateway_class_instances_obj.verifyPaymentSignature(**params2)
                if payment_gateway_verify_rsp_obj["status_code"]>0:
                    print("step0")    
                    # updating the payment order table status
                    cnt_of_payment_orders_row_updated = await self.payment_repo.update_payment_orders_details(
                        where_data = {
                            PaymentOrders.id == payment_order.id,
                        },
                        update_data = {
                            "gateway_payment_id" : gateway_payment_id,
                            "gateway_signature" : gateway_payment_signature,
                            "failure_reason" : "ss" if payment_gateway_verify_rsp_obj["status_code"] == 200 else "Payment signature verification failed",
                            "version" : PaymentOrders.version + 1,
                            "status" : "CAPTURED" if payment_gateway_verify_rsp_obj["status_code"] == 200 else "FAILED",
                        }
                    )
                    print("step1")
                    # creating payment audit logs into table
                    created_payment_audit_logs_row = await self.payment_repo.create_payment_audit_logs(
                        payment_order_id=payment_order.id,
                        action="SIGNATURE_VERIFIED" if payment_gateway_verify_rsp_obj["status_code"] == 200 else "SIGNATURE_VERIFICATION_FAILED",
                        gateway_response=None,
                        metadata_json={
                            "gateway_payment_id" : gateway_payment_id,
                            "gateway_signature" : gateway_payment_signature,
                        },
                        status="A"
                    )
                    print("step2")
                    # adding records into outbox events table
                    # data published into kafka-topics via workers and consumer will be consume the message
                    params1 = {
                        "payment_order_id": payment_order.id,
                        "gateway_order_id": payment_order.gateway_order_id,
                        "gateway_payment_id": gateway_payment_id,
                        "amount": str(payment_order.total_amount),
                        "reason": ",".join(payment_gateway_verify_rsp_obj["messages"]),
                        "payment_order_status": "CAPTURED" if payment_gateway_verify_rsp_obj["status_code"] == 200 else "FAILED",
                    }
                    rsp = await self.store_payment_updated_status_into_outbox_events(payload=params1)

                    print("step3")

                    await self._db_session.commit()
                    
                    return standardize_response(
                        status_code=payment_gateway_verify_rsp_obj["status_code"],
                        messages=payment_gateway_verify_rsp_obj["messages"],
                        data={
                            "booking_id" : payment_order.booking_id,
                            "payment_order_id" : payment_order.id,
                            "gateway_order_id" : payment_order.gateway_order_id,
                            "gateway_payment_id" : gateway_payment_id,
                            "payment_order_status" : "CAPTURED" if payment_gateway_verify_rsp_obj["status_code"] == 200 else "FAILED",
                        }
                    )

    
        except Exception as e:
            import sys
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print("Line number:", exc_tb.tb_lineno)
            await self._db_session.rollback()
            return standardize_response(
                status_code=500,
                messages=[f"{str(e)}"]
            )


    async def store_payment_updated_status_into_outbox_events(
        self,
        payload: dict
    ):

        rsp = {
            "outbox_event_id" : 0
        }
        try:
            
            created_outbox_events_row = await self.outbox_repo.add_outbox_event(
                aggregate_type="PAYMENT_ORDERS",
                aggregate_id=payload.get("schedule_id", 0),
                event_type="PAYMENT_ORDERS_UPDATED_STATUS",
                payload_json={
                    "payment_order_id": payload.get("payment_order_id", 0),
                    "gateway_order_id": payload.get("gateway_order_id", ""),
                    "gateway_payment_id": payload.get("gateway_payment_id", ""),
                    "amount": str(payload.get("amount", 0)),
                    "reason": payload.get("reason", "")[:90],
                    "payment_order_status": payload.get("payment_order_status", ""),
                },
                status="PENDING"
            )
            rsp = {
                "outbox_event_id" : created_outbox_events_row.id
            }
            
        except Exception as e:
            print(f"store_payment_updated_status_into_outbox_events func ex: {str(e)}")

        return rsp


