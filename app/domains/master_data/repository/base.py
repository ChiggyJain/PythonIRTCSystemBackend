
from datetime import date
from abc import ABC, abstractmethod
from typing import Any
from app.domains.master_data.models.stations_models import Stations
from app.domains.master_data.models.trains_models import Trains
from app.domains.master_data.models.seats_models import Seats
from app.domains.master_data.models.routes_models import Routes
from app.domains.master_data.models.routestations_models import RouteStations
from app.domains.master_data.models.schedules_models import Schedules


class MasterDataRepositoryBase(ABC):

    @abstractmethod
    async def create_station(
        self,
        *,
        name: str,
        code: str,
        city: str,
        state: str,
        status: str = "A",
    ) -> Stations:
        pass
    
    
    @abstractmethod
    async def create_train(
        self,
        *,
        train_number: str,
        train_name: str,
        coach_name: str,
        total_seats: int,
        status: str = "A",
    ) -> Trains:
        pass
    
    @abstractmethod
    async def create_seats(
        self,
        *,
        train_id: int,
        seat_details: list[dict[str, Any]],
        status: str = "A",
    ) -> list[Seats]:
        pass
    
    @abstractmethod
    async def train_exists(self, *, train_id: int) -> bool:
        pass

    @abstractmethod
    async def count_existing_station_ids(
        self,
        *,
        station_ids: list[int],
    ) -> int:
        pass

    @abstractmethod
    async def create_route(
        self,
        *,
        train_id: int,
        status: str = "A",
    ) -> Routes:
        pass

    @abstractmethod
    async def create_route_stations(
        self,
        *,
        route_id: int,
        station_details: list[dict[str, Any]],
        status: str = "A",
    ) -> list[RouteStations]:
        pass

    
    @abstractmethod
    async def get_route_by_train_id(
        self,
        *,
        train_id: int,
    ) -> Routes | None:
        pass

    @abstractmethod
    async def get_route_stations_by_route_id(
        self,
        *,
        route_id: int,
    ) -> list[RouteStations]:
        pass

    @abstractmethod
    async def create_schedule(
        self,
        *,
        train_id: int,
        departure_date: date,
        status: str = "A",
    ) -> Schedules:
        pass


    @abstractmethod
    async def add_outbox_event(
        self,
        *,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload_json: dict[str, Any],
        status: str,
    ) -> None:
        pass


    @abstractmethod
    async def commit(self) -> None:
        pass

    @abstractmethod
    async def rollback(self) -> None:
        pass
