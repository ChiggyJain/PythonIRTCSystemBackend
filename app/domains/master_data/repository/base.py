
from abc import ABC, abstractmethod
from typing import Any
from app.domains.master_data.stations_model import Stations
from app.domains.master_data.trains_model import Trains
from app.domains.master_data.seats_model import Seats


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
        """
        Example:
        create_train(
            train_number="TRAIN1233",
            train_name="T1",
            coach_name="AC",
            total_seats=20,
        )
        """
        pass
    
    @abstractmethod
    async def create_seats(
        self,
        *,
        train_id: int,
        seat_details: list[dict[str, Any]],
        status: str = "A",
    ) -> list[Seats]:
        """
        Example seat_details:
        [
            {"seat_number": 1, "seat_type": "LOWER", "price": 500},
            {"seat_number": 2, "seat_type": "UPPER", "price": 300},
        ]
        """
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
