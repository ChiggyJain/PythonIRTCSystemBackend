
from datetime import date
from typing import Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.master_data.models.stations_model import Stations
from app.domains.master_data.models.trains_model import Trains
from app.domains.master_data.models.seats_model import Seats
from app.domains.master_data.models.routes_model import Routes
from app.domains.master_data.models.routestations_model import RouteStations
from app.domains.master_data.models.schedules_model import Schedules
from app.domains.master_data.repository.base import MasterDataRepositoryBase
from app.domains.security.models.models import OutboxEvents
from app.common.utils.datetime import now_ist


class MasterDataSQLAlchemyRepository(MasterDataRepositoryBase):

    def __init__(self, db: AsyncSession):
        self.db = db


    async def create_station(
        self,
        *,
        name: str,
        code: str,
        city: str,
        state: str,
        status: str = "A",
    ) -> Stations:
        row = Stations(
            name=name,
            code=code,
            city=city,
            state=state,
            status=status,
            created_at=now_ist(),
            updated_at=now_ist(),
        )
        self.db.add(row)
        # temporary stored data in memory not actual db level
        await self.db.flush()
        return row


    async def create_train(
        self,
        *,
        train_number: str,
        train_name: str,
        coach_name: str,
        total_seats: int,
        status: str = "A",
    ) -> Trains:
        # Create train row first; flush gives generated train_id
        row = Trains(
            train_number=train_number,
            train_name=train_name,
            coach_name=coach_name,
            total_seats=total_seats,
            status=status,
            created_at=now_ist(),
            updated_at=now_ist(),
        )
        self.db.add(row)
        # temporary stored data in memory not actual db level
        await self.db.flush()
        return row
    

    async def create_seats(
        self,
        *,
        train_id: int,
        seat_details: list[dict[str, Any]],
        status: str = "A",
    ) -> list[Seats]:
        # Bulk-create seats for same train_id in same transaction
        rows: list[Seats] = []
        for seat in seat_details:
            row = Seats(
                train_id=train_id,
                seat_number=seat["seat_number"],
                seat_type=seat["seat_type"],
                price=seat["price"],
                status=status,
                created_at=now_ist(),
                updated_at=now_ist(),
            )
            rows.append(row)
        self.db.add_all(rows)
        # temporary stored data in memory not actual db level
        await self.db.flush()
        return rows
    

    async def train_exists(self, *, train_id: int) -> bool:
        stmt = (
            select(Trains.id)
            .where(
                Trains.id == train_id,
                Trains.status == "A",
            )
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None
    

    async def count_existing_station_ids(self, *, station_ids: list[int],) -> int:
        if not station_ids:
            return 0
        stmt = select(func.count(Stations.id)).where(
            Stations.id.in_(station_ids),
            Stations.status == "A",
        )
        result = await self.db.execute(stmt)
        return int(result.scalar_one())
    

    async def create_route(self, *, train_id: int, status: str = "A",) -> Routes:
        row = Routes(
            train_id=train_id,
            status=status,
            created_at=now_ist(),
            updated_at=now_ist(),
        )
        self.db.add(row)
        # temporary stored data in memory not actual db level
        await self.db.flush()
        return row

    async def create_route_stations(
        self,
        *,
        route_id: int,
        station_details: list[dict[str, Any]],
        status: str = "A",
    ) -> list[RouteStations]:
        
        rows: list[RouteStations] = []
        for item in station_details:
            row = RouteStations(
                route_id=route_id,
                station_id=item["station_id"],
                sequence_number=item["sequence_number"],
                arrival_time=item["arrival_time"],
                departure_time=item["departure_time"],
                distance_from_origin=item["distance_from_origin"],
                status=status,
                created_at=now_ist(),
                updated_at=now_ist(),
            )
            rows.append(row)
        self.db.add_all(rows)
        # temporary stored data in memory not actual db level
        await self.db.flush()
        return rows
    

    async def get_route_by_train_id(
        self,
        *,
        train_id: int,
    ) -> Routes | None:
        stmt = (
            select(Routes)
            .where(
                Routes.train_id == train_id,
                Routes.status == "A",
            )
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()


    async def get_route_stations_by_route_id(
        self,
        *,
        route_id: int,
    ) -> list[RouteStations]:
        stmt = (
            select(RouteStations)
            .where(
                RouteStations.route_id == route_id,
                RouteStations.status == "A",
            )
            .order_by(RouteStations.sequence_number.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


    async def create_schedule(
        self,
        *,
        train_id: int,
        departure_date: date,
        status: str = "A",
    ) -> Schedules:
        row = Schedules(
            train_id=train_id,
            departure_date=departure_date,
            status=status,
            created_at=now_ist(),
            updated_at=now_ist(),
        )
        self.db.add(row)
        await self.db.flush()
        # temporary stored data in memory not actual db level
        return row


    async def add_outbox_event(
        self,
        *,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload_json: dict[str, Any],
        status: str,
    ) -> None:
        row = OutboxEvents(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload_json=payload_json,
            status=status,
            retry_count=0,
            next_retry_at=None,
            last_error=None,
            published_at=None,
            created_at=now_ist(),
            updated_at=now_ist(),
        )
        self.db.add(row)
        await self.db.flush()


    async def commit(self) -> None:
        await self.db.commit()

    async def rollback(self) -> None:
        await self.db.rollback()
