
from datetime import date
from decimal import Decimal
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.utils.datetime import now_ist
from app.domains.inventory.models.schedule_inventory_models import ScheduleInventory
from app.domains.inventory.models.seat_inventory_models import SeatInventory
from app.domains.inventory.models.route_stop_models import RouteStop
from app.domains.inventory.models.seat_segment_lock_models import SeatSegmentLockInventory


class InventorySQLAlchemyRepository:

    def __init__(self, db_session: AsyncSession):
        self._db_session = db_session


    async def get_inventory_schedules_by_schedule_id(
        self,
        schedule_id: int,
    ) -> ScheduleInventory | None:

        stmt = select(ScheduleInventory).where(
            ScheduleInventory.schedule_id == schedule_id
        )
        res = await self._db_session.execute(stmt)
        return res.scalar_one_or_none()
    

    async def lock_seats_inventory_for_booking(
        self,
        *,
        schedule_id: int,
        seat_ids : List[int],
    ) -> list[SeatInventory]:

        conditions = [
            SeatInventory.schedule_id == schedule_id,
            SeatInventory.seat_id.in_(seat_ids),
        ]            
        stmt = (
            select(SeatInventory)
            .where(*conditions)
            .with_for_update(skip_locked=True)
        )            
        res = await self._db_session.execute(stmt)
        return list(res.scalars().all())
    

    async def lock_seats_segment_for_booking(
        self,
        *,
        schedule_id: int,
        seat_ids : List[int],
        from_station_sequence_number: int,
        to_station_sequence_number: int,
    ) -> list[SeatSegmentLockInventory]:

        conditions = [
            SeatSegmentLockInventory.schedule_id == schedule_id,
            SeatSegmentLockInventory.seat_id.in_(seat_ids),
            SeatSegmentLockInventory.status.in_(["LOCKED", "BOOKED"]),
            SeatSegmentLockInventory.from_station_sequence_number < to_station_sequence_number,
            SeatSegmentLockInventory.to_station_sequence_number > from_station_sequence_number,
        ]            
        stmt = (
            select(SeatInventory)
            .where(*conditions)
            .with_for_update(skip_locked=True)
        )            
        res = await self._db_session.execute(stmt)
        return list(res.scalars().all())
    

    async def add_schedule_inventory(
        self,
        *,
        schedule_id: int,
        train_id: int,
        train_number: str,
        train_name: str,
        departure_date: date,
        total_seats: int,
        available_seats: int,
        locked: int,
        booked: int,
        status: str = "ACTIVE",
        version: int = 0,
    ) -> ScheduleInventory:
        
        row = ScheduleInventory(
            schedule_id=schedule_id,
            train_id=train_id,
            train_number=train_number,
            train_name=train_name,
            departure_date=departure_date,
            total_seats=total_seats,
            available_seats=available_seats,
            locked=locked,
            booked=booked,
            version=version,
            created_at=now_ist(),
            updated_at=now_ist(),
            status=status,
        )
        self._db_session.add(row)
        await self._db_session.flush()
        return row


    async def add_seat_inventory_bulk(
        self,
        *,
        schedule_inventory_id: int,
        schedule_id: int,
        seat_details: list[dict],
    ) -> None:
        
        rows: list[SeatInventory] = []
        for seat in seat_details:
            price_value = seat.get("price", 0)
            if not isinstance(price_value, Decimal):
                price_value = Decimal(str(price_value))
            rows.append(
                SeatInventory(
                    schedule_inventory_id=schedule_inventory_id,
                    schedule_id=schedule_id,
                    seat_id=int(seat.get("id", 0)),
                    seat_number=int(seat.get("seat_number", 0)),
                    seat_type=str(seat.get("seat_type", "LOWER")),
                    price=price_value,
                    created_at=now_ist(),
                    updated_at=now_ist(),
                    status="AVAILABLE",
                )
            )

        self._db_session.add_all(rows)
        await self._db_session.flush()


    async def add_route_stop_bulk(
        self,
        *,
        schedule_id: int,
        station_details: list[dict],
    ) -> None:
        
        rows: list[RouteStop] = []
        for station in station_details:
            rows.append(
                RouteStop(
                    schedule_id=schedule_id,
                    station_id=int(station.get("station_id", 0)),
                    station_name=str(station.get("name", "")),
                    station_code=str(station.get("code", "")),
                    sequence_number=int(station.get("sequence_number", 0)),
                    status="ACTIVE",
                    created_at=now_ist(),
                    updated_at=now_ist(),
                )
            )

        self._db_session.add_all(rows)
        await self._db_session.flush()

    
    async def add_seat_segement_lock_bulk_for_booking(
        self,
        *,
        schedule_id: int,
        seat_details: list[dict],
    ) -> None:
        
        rows: list[SeatSegmentLockInventory] = []
        for seat in seat_details:
            rows.append(
                SeatSegmentLockInventory(
                    schedule_id=schedule_id,
                    seat_id=int(seat.get("id", 0)),
                    from_station_sequence_number=int(seat.get("from_station_sequence_number", 0)),
                    to_station_sequence_number=int(seat.get("to_station_sequence_number", 0)),
                    locked_by_user_id=int(seat.get("locked_by_user_id", 0)),
                    locked_at=now_ist(),
                    locked_expires_at=seat.get("locked_expires_at", ""),
                    created_at=now_ist(),
                    updated_at=now_ist(),
                    status=seat.get("status", "LOCKED"),
                )
            )
        self._db_session.add_all(rows)
        await self._db_session.flush()
