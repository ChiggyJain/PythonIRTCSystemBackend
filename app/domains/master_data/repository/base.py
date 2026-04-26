
from abc import ABC, abstractmethod
from typing import Any
from app.domains.master_data.stations_model import Stations


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
