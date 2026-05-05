
from datetime import date
from typing import Any
from typing import List, Dict
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.master_data.models.stations_models import Stations
from app.domains.master_data.models.trains_models import Trains
from app.domains.master_data.models.seats_models import Seats
from app.domains.master_data.models.routes_models import Routes
from app.domains.master_data.models.route_stations_models import RouteStations
from app.domains.master_data.models.schedules_models import Schedules
from app.domains.master_data.repository.base import MasterDataRepositoryBase
from app.infrastructure.outbox.models.outbox_events_models import OutboxEvents
from app.common.utils.datetime import now_ist


class MasterDataSQLAlchemyRepository(MasterDataRepositoryBase):

    def __init__(self, db_session: AsyncSession):
        self._db_session = db_session


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
        self._db_session.add(row)
        await self._db_session.flush()
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
        
        row = Trains(
            train_number=train_number,
            train_name=train_name,
            coach_name=coach_name,
            total_seats=total_seats,
            status=status,
            created_at=now_ist(),
            updated_at=now_ist(),
        )
        self._db_session.add(row)
        await self._db_session.flush()
        return row
    

    async def create_seats(
        self,
        *,
        train_id: int,
        seat_details: list[dict[str, Any]],
        status: str = "A",
    ) -> list[Seats]:
        
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
        self._db_session.add_all(rows)
        await self._db_session.flush()
        return rows
    

    async def get_train_by_id(self, *, train_id: int) -> Trains | None:
        stmt = (
            select(Trains)
            .where(
                Trains.id == train_id,
                Trains.status == "A",
            )
            .limit(1)
        )
        result = await self._db_session.execute(stmt)
        return result.scalar_one_or_none()
    

    async def count_existing_station_ids(self, *, station_ids: list[int],) -> int:
        if not station_ids:
            return 0
        stmt = select(func.count(Stations.id)).where(
            Stations.id.in_(station_ids),
            Stations.status == "A",
        )
        result = await self._db_session.execute(stmt)
        return int(result.scalar_one())
    

    async def create_route(self, *, train_id: int, status: str = "A",) -> Routes:
        row = Routes(
            train_id=train_id,
            status=status,
            created_at=now_ist(),
            updated_at=now_ist(),
        )
        self._db_session.add(row)
        await self._db_session.flush()
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
        self._db_session.add_all(rows)
        await self._db_session.flush()
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
        result = await self._db_session.execute(stmt)
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
        result = await self._db_session.execute(stmt)
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
        self._db_session.add(row)
        await self._db_session.flush()
        return row


    async def get_train_seats_by_train_id(
        self,
        *,
        train_id: int,
    ) -> list[Seats]:
        
        stmt = (
            select(Seats)
            .where(
                Seats.train_id == train_id,
                Seats.status == "A",
            )
            .order_by(Seats.seat_number.asc())
        )
        result = await self._db_session.execute(stmt)
        return list(result.scalars().all())
    

    async def get_station_by_station_ids(
        self,
        *,
        station_ids: List[int],
    ) -> List[Stations] | None:
        
        stmt = (
            select(Stations)
            .where(
                Stations.id.in_(station_ids),
                Stations.status == "A",
            )
        )
        result = await self._db_session.execute(stmt)
        return result.scalars().all()
    


    async def commit(self) -> None:
        await self._db_session.commit()

    async def rollback(self) -> None:
        await self._db_session.rollback()
