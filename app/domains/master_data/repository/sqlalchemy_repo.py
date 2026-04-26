
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.master_data.stations_model import Stations
from app.domains.master_data.repository.base import MasterDataRepositoryBase
from app.domains.security.models import OutboxEvents
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
        await self.db.flush()
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
