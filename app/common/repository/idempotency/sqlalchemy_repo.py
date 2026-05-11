
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any
from app.common.utils.datetime import now_ist
from app.common.models.idempotencyrecord_models import IdempotencyRecords


class IdempotencySQLAlchemyRepository:

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session


    async def get_idempotency_record_by_event_key(self, event_key: str) -> IdempotencyRecords | None:
        stmt = select(IdempotencyRecords).where(IdempotencyRecords.event_key == event_key)
        result = await self.db_session.execute(stmt)
        return result.scalar_one_or_none()


    async def add_idempotency_record(
        self, 
        *, 
        event_key: str, 
        event_type: str | None = None, 
        event_response: dict[str, Any] | None = None
    ) -> IdempotencyRecords:
        
        row = IdempotencyRecords(
            event_key=event_key,
            event_type=event_type,
            event_response=event_response,
            created_at=now_ist(),
            updated_at=now_ist(),
        )
        self.db_session.add(row)
        await self.db_session.flush()
        return row

