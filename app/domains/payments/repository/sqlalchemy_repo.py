

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any
from sqlalchemy import select, update, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.utils.datetime import now_ist
from app.domains.payments.models.payment_orders_models import PaymentOrders
from app.domains.payments.models.refund_orders_models import RefundOrders
from app.domains.payments.models.payment_audit_logs_models import PaymentAuditLogs


class PaymentSQLAlchemyRepository:

    def __init__(self, db_session: AsyncSession):
        self._db_session = db_session


    async def create_payment_orders(
        self,
        *,
        idempotency_key: str,
        booking_id: int,
        user_id: int,
        total_amount: int,
        currency: str = "INR",
        gateway_provider: str,
        gateway_order_id: str,
        gateway_payment_id: str | None = None,
        gateway_signature: str,
        failure_reason: str | None = None,
        metadata_json: dict[str, Any] | None,
        version: int = 0,
        status: str = "CREATED"
    ) -> PaymentOrders:
        
        row = PaymentOrders(
            idempotency_key=idempotency_key,
            booking_id=booking_id,
            user_id=user_id,
            total_amount=total_amount,
            currency=currency,
            gateway_provider=gateway_provider,
            gateway_order_id=gateway_order_id,
            gateway_payment_id=gateway_payment_id,
            gateway_signature=gateway_signature,
            failure_reason=failure_reason,
            metadata_json=metadata_json,
            version=version,
            created_at=now_ist(),
            updated_at=now_ist(),
            status=status,
        )
        self._db_session.add(row)
        await self._db_session.flush()
        return row
    