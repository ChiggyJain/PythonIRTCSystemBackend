

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any
from sqlalchemy import select, update, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.utils.datetime import now_ist
from app.domains.booking.models.bookings_models import Bookings
from app.domains.booking.models.booking_seats_models import BookingSeats
from app.domains.booking.models.booking_passgenger_models import BookingPassengers
from app.domains.booking.models.booking_saga_logs_models import BookingSagaLogs


class BookingSQLAlchemyRepository:

    def __init__(self, db_session: AsyncSession):
        self.db = db_session



    async def get_booking_saga_logs_by_booking_id(
        self,
        *,
        booking_id: int,
        status: str
    ) -> list[BookingSagaLogs]:
        
        stmt = (
            select(BookingSagaLogs)
            .where(
                BookingSagaLogs.booking_id == booking_id,
                BookingSagaLogs.status == status
            )
            .order_by(BookingSagaLogs.created_at.desc())
        )
        result = await self._db_session.execute(stmt)
        return list(result.scalars().all())
    

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
    

    async def create_booking_seats(
        self,
        *,
        booking_id: int,
        seat_details: list[dict[str, Any]],
    ) -> list[BookingSeats]:
        
        rows: list[BookingSeats] = []
        for item in seat_details:
            row = BookingSeats(
                booking_id=booking_id,
                seat_id=item["seat_id"],
                seat_number=item["seat_number"],
                seat_type=item["seat_type"],
                price=item["price"],
                status="ACTIVE",
                created_at=now_ist(),
                updated_at=now_ist(),
            )
            rows.append(row)
        self._db_session.add_all(rows)
        await self._db_session.flush()
        return rows
    

    async def create_booking_passengers(
        self,
        *,
        booking_id: int,
        passenger_details: list[dict[str, Any]],
    ) -> list[BookingPassengers]:
        
        rows: list[BookingPassengers] = []
        for item in passenger_details:
            row = BookingPassengers(
                booking_id=booking_id,
                seat_id=item["seat_id"],
                name=item["name"],
                age=item["age"],
                gender=item["gender"],
                status="ACTIVE",
                created_at=now_ist(),
                updated_at=now_ist(),
            )
            rows.append(row)
        self._db_session.add_all(rows)
        await self._db_session.flush()
        return rows
    

    async def create_booking_saga_logs(
        self,
        *,
        booking_id: int,
        saga_step: str = "HOLD_SEATS",
        request: dict[str, Any] | None,
        response: dict[str, Any] | None,
        error: str | None = None,
        status: str = "PENDING"
    ) -> BookingSagaLogs:
        
        row = BookingSagaLogs(
            booking_id=booking_id,
            saga_step=saga_step,
            request=request,
            response=response,
            error=error,
            status=status,
            created_at=now_ist(),
            updated_at=now_ist(),
        )
        self._db_session.add(row)
        await self._db_session.flush()
        return row
    

    async def update_booking_saga_logs_by_id(
        self,
        *,
        where_data: dict,
        update_data: dict,
    ) -> bool:

        update_data["updated_at"] = now_ist()
        stmt = update(BookingSagaLogs)
        for key, value in where_data.items():
            stmt = stmt.where(
                getattr(BookingSagaLogs, key) == value
            )
        stmt = stmt.values(**update_data)
        res = await self._db_session.execute(stmt)
        return bool(res.rowcount and res.rowcount > 0)
    

    async def update_booking_by_id(
        self,
        *,
        where_data: dict,
        update_data: dict,
    ) -> bool:

        update_data["updated_at"] = now_ist()
        stmt = update(Bookings)
        for key, value in where_data.items():
            stmt = stmt.where(
                getattr(BookingSagaLogs, key) == value
            )
        stmt = stmt.values(**update_data)
        res = await self._db_session.execute(stmt)
        return bool(res.rowcount and res.rowcount > 0)

    