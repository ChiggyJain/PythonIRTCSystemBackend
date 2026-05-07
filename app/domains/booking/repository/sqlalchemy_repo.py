

from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.utils.datetime import now_ist
from app.domains.booking.models.bookings_models import Bookings


class BookingSQLAlchemyRepository:

    def __init__(self, db_session: AsyncSession):
        self.db = db_session


    async def create_booking(
        self,
        *,
        user_id: int,
        schedule_id: int,
        train_id: int,
        train_number: str,
        train_name: str,
        departure_date: date,
        total_amount: Decimal,
        seat_count: int,
        from_station_id: int,
        to_station_id: int,
        from_station_sequence_number: int,
        to_station_sequence_number: int,
        idempotency_key: str,
        payment_order_id: int | None = None,
        locked_expires_at: date,
        failure_reason: str | None = None,
        version: int = 0,
        status: str = "PENDING"
    ) -> Bookings:
        
        row = Bookings(
            user_id=user_id,
            schedule_id=schedule_id,
            train_id=train_id,
            train_number=train_number,
            train_name=train_name,
            departure_date=departure_date,
            total_amount=total_amount,
            seat_count=seat_count,
            from_station_id=from_station_id,
            to_station_id=to_station_id,
            from_station_sequence_number=from_station_sequence_number,
            to_station_sequence_number=to_station_sequence_number,
            idempotency_key=idempotency_key,
            payment_order_id=payment_order_id,
            locked_expires_at=locked_expires_at,
            failure_reason=failure_reason,
            version=version,
            status=status,
            created_at=now_ist(),
            updated_at=now_ist(),
        )
        self._db_session.add(row)
        await self._db_session.flush()
        return row
    