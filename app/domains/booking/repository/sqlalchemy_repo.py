

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any
from typing import Any, List, Optional
from sqlalchemy import select
from sqlalchemy import select, update, or_
from sqlalchemy.sql import Select
from collections import defaultdict
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.utils.datetime import now_ist
from app.domains.booking.models.bookings_models import Bookings
from app.domains.booking.models.booking_seats_models import BookingSeats
from app.domains.booking.models.booking_passgenger_models import BookingPassengers
from app.domains.booking.models.booking_saga_logs_models import BookingSagaLogs


class BookingSQLAlchemyRepository:

    def __init__(self, db_session: AsyncSession):
        self._db_session = db_session


    
    async def get_user_bookings(
        self,
        user_id: int,
        status: str | None = None,
        page: int = 1,
        limit: int = 10,
    ):

        skip = (page - 1) * limit

        booking_query = select(Bookings).where(
            Bookings.user_id == user_id
        )
        count_query = select(func.count()).select_from(Bookings).where(
            Bookings.user_id == user_id
        )

        if status:
            booking_query = booking_query.where(
                Bookings.status == status.upper()
            )
            count_query = count_query.where(
                Bookings.status == status.upper()
            )

        booking_query = (
            booking_query
            .order_by(Bookings.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        bookings_result = await self._db_session.execute(booking_query)
        bookings = bookings_result.scalars().all()
        total_result = await self._db_session.execute(count_query)
        total = total_result.scalar()

        if not bookings:
            return {
                "bookings": [],
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "totalPages": 0,
                }
            }

        booking_ids = [b.id for b in bookings]

        seats_result = await self._db_session.execute(
            select(BookingSeats)
            .where(BookingSeats.booking_id.in_(booking_ids))
            .order_by(BookingSeats.seat_number.asc())
        )
        seats = seats_result.scalars().all()

        passengers_result = await self._db_session.execute(
            select(BookingPassengers)
            .where(BookingPassengers.booking_id.in_(booking_ids))
        )
        passengers = passengers_result.scalars().all()

        seats_map = defaultdict(list)
        for seat in seats:
            seats_map[seat.booking_id].append({
                "seat_id": seat.seat_id,
                "seat_number": seat.seat_number,
                "seat_type": seat.seat_type,
                "price": str(seat.price),
            })

        passengers_map = defaultdict(list)
        for passenger in passengers:
            passengers_map[passenger.booking_id].append({
                "name": passenger.name,
                "age": passenger.age,
                "gender": passenger.gender,
            })

        response = []
        for booking in bookings:
            response.append({
                "booking_id": booking.id,
                "schedule_id" : booking.schedule_id,
                "train_id" : booking.train_id,
                "train_number" : booking.train_number,
                "train_name" : booking.train_name,
                "from_station_sequence_number" : booking.from_station_sequence_number,
                "to_station_sequence_number" : booking.to_station_sequence_number,
                "departure_date" : str(booking.departure_date),
                "seats": seats_map.get(booking.id, []),
                "passengers": passengers_map.get(booking.id, []),
                "total_amount": str(booking.total_amount),
                "created_at": str(booking.created_at),
                "booking_status": booking.status,
            })

        return {
            "bookings": response,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "totalPages": (total + limit - 1) // limit,
            }
        }

    
    async def get_booking_details(
        self, 
        select_columns: Optional[List[Any]] = None,
        where_conditions: Optional[List[Any]] = None,
        order_by: Optional[List[Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Bookings] | None:

        if select_columns:
            stmt: Select = select(*select_columns)
        else:
            stmt: Select = select(Bookings)

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
    

    async def get_booking_seats_details(
        self, 
        select_columns: Optional[List[Any]] = None,
        where_conditions: Optional[List[Any]] = None,
        order_by: Optional[List[Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[BookingSeats] | None:

        if select_columns:
            stmt: Select = select(*select_columns)
        else:
            stmt: Select = select(BookingSeats)

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
    

    async def get_booking_passengers_details(
        self, 
        select_columns: Optional[List[Any]] = None,
        where_conditions: Optional[List[Any]] = None,
        order_by: Optional[List[Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[BookingPassengers] | None:

        if select_columns:
            stmt: Select = select(*select_columns)
        else:
            stmt: Select = select(BookingPassengers)

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
    
    

    async def get_booking_saga_logs_details(
        self, 
        select_columns: Optional[List[Any]] = None,
        where_conditions: Optional[List[Any]] = None,
        order_by: Optional[List[Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[BookingSagaLogs] | None:

        if select_columns:
            stmt: Select = select(*select_columns)
        else:
            stmt: Select = select(BookingSagaLogs)

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
                seat_id=item.get("seat_id", 0),
                seat_number=item.get("seat_number", 0),
                seat_type=item.get("seat_type", "LOWER"),
                price=item.get("price", 0.00),
                created_at=now_ist(),
                updated_at=now_ist(),
                status="ACTIVE",
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
                seat_id=item.get("seat_id", 0),
                name=item.get("name", "Default"),
                age=item.get("age", 1),
                gender=item.get("gender", "Male"),
                created_at=now_ist(),
                updated_at=now_ist(),
                status=item.get("status", "ACTIVE"),
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
            created_at=now_ist(),
            updated_at=now_ist(),
            status=status,
        )
        self._db_session.add(row)
        await self._db_session.flush()
        return row
    

    async def update_booking_saga_logs_details(
        self,
        *,
        where_data: dict,
        update_data: dict,
    ) -> bool:

        update_data["updated_at"] = now_ist()
        conditions = []
        for key, value in where_data.items():
            column = getattr(BookingSagaLogs, key)
            if isinstance(value, list):
                conditions.append(column.in_(value))
            else:
                conditions.append(column == value)
        stmt = (
            update(BookingSagaLogs)
            .where(*conditions)
            .values(**update_data)
        )        
        res = await self._db_session.execute(stmt)
        return bool(res.rowcount and res.rowcount > 0)
    

    async def update_booking_details(
        self,
        *,
        where_data: dict,
        update_data: dict,
    ) -> bool:

        update_data["updated_at"] = now_ist()
        conditions = []
        for key, value in where_data.items():
            column = getattr(Bookings, key)
            if isinstance(value, list):
                conditions.append(column.in_(value))
            else:
                conditions.append(column == value)
        stmt = (
            update(Bookings)
            .where(*conditions)
            .values(**update_data)
        )        
        res = await self._db_session.execute(stmt)
        return bool(res.rowcount and res.rowcount > 0)