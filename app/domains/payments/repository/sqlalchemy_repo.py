

from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy import select, update, or_
from typing import Any, List, Optional
from sqlalchemy.sql import Select
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.utils.datetime import now_ist
from app.domains.payments.models.payment_orders_models import PaymentOrders
from app.domains.payments.models.refund_orders_models import RefundOrders
from app.domains.payments.models.payment_audit_logs_models import PaymentAuditLogs


class PaymentSQLAlchemyRepository:

    def __init__(self, db_session: AsyncSession):
        self._db_session = db_session


    async def get_payment_orders_details(
        self, 
        select_columns: Optional[List[Any]] = None,
        where_conditions: Optional[List[Any]] = None,
        order_by: Optional[List[Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[PaymentOrders] | None:

        if select_columns:
            stmt: Select = select(*select_columns)
        else:
            stmt: Select = select(PaymentOrders)

        if where_conditions:
            stmt = stmt.where(*where_conditions)

        if order_by:
            stmt = stmt.order_by(*order_by)

        if limit:
            stmt = stmt.limit(limit)

        if offset:
            stmt = stmt.offset(offset)

        result = await self._db_session.execute(stmt)

        if select_columns:
            return result.mappings().all()

        return list(result.scalars().all())




    async def create_payment_orders(
        self,
        *,
        idempotency_key: str,
        booking_id: int,
        user_id: int,
        total_amount: Decimal,
        currency: str = "INR",
        gateway_provider: str,
        gateway_order_id: str,
        gateway_payment_id: str | None = None,
        gateway_signature: str | None = None,
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
    

    async def create_refund_orders(
        self,
        *,
        idempotency_key: str,
        payment_order_id: int,
        total_amount: Decimal,
        reason: str,
        gateway_refund_id: str | None = None,
        failure_reason: str | None = None,
        metadata_json: dict[str, Any] | None,
        status: str = "INITIATED"
    ) -> RefundOrders:
        
        row = RefundOrders(
            idempotency_key=idempotency_key,
            payment_order_id=payment_order_id,
            total_amount=total_amount,
            reason=reason,
            gateway_refund_id=gateway_refund_id,
            failure_reason=failure_reason,
            metadata_json=metadata_json,
            created_at=now_ist(),
            updated_at=now_ist(),
            status=status,
        )
        self._db_session.add(row)
        await self._db_session.flush()
        return row
    
    
    async def create_payment_audit_logs(
        self,
        *,
        payment_order_id: int,
        action: str | None = None,
        gateway_response: dict[str, Any] | None,
        metadata_json: dict[str, Any] | None,
        status: str = "A"
    ) -> PaymentAuditLogs:
        
        row = PaymentAuditLogs(
            payment_order_id=payment_order_id,
            action=action,
            gateway_response=gateway_response,
            metadata_json=metadata_json,
            created_at=now_ist(),
            updated_at=now_ist(),
            status=status,
        )
        self._db_session.add(row)
        await self._db_session.flush()
        return row
    

    async def update_payment_orders_details(
        self,
        *,
        where_data: dict,
        update_data: dict,
    ) -> bool:

        update_data["updated_at"] = now_ist()
        conditions = []
        for key, value in where_data.items():
            column = getattr(PaymentOrders, key)
            if isinstance(value, list):
                conditions.append(column.in_(value))
            else:
                conditions.append(column == value)
        stmt = (
            update(PaymentOrders)
            .where(*conditions)
            .values(**update_data)
        )
        res = await self._db_session.execute(stmt)
        return bool(res.rowcount and res.rowcount > 0)
    