"""
OutboxEvents SQLAlchemy Repository
"""

from datetime import datetime
from typing import Any
from sqlalchemy import select, update, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.outbox.models.outbox_events_models import OutboxEvents
from app.infrastructure.outbox.repository.base import OutboxEventsRepositoryBase
from app.common.utils.datetime import now_ist


class OutboxEventsSQLAlchemyRepository(OutboxEventsRepositoryBase):

    def __init__(
        self,
        db_session: AsyncSession,
    ):
        self._db_session = db_session


    async def add_outbox_event(
        self,
        *,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload_json: dict[str, Any],
        status: str,
    ) -> OutboxEvents:

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
        self._db_session.add(row)
        await self._db_session.flush()
        return row


    async def get_by_id(
        self,
        id: int,
    ) -> OutboxEvents | None:

        stmt = select(OutboxEvents).where(
            OutboxEvents.id == id
        )
        result = await self._db_session.execute(stmt)
        return result.scalar_one_or_none()
    
    
    async def fetch_pending_outbox_events(
        self,
        *,
        aggregate_type: str | None = None,
        aggregate_id: int | None = None,
        event_type: str | None = None,
        limit: int = 1,
        now_time: datetime,
    ) -> list[OutboxEvents]:

        conditions = [
            OutboxEvents.status == "PENDING",
            or_(
                OutboxEvents.next_retry_at.is_(None),
                OutboxEvents.next_retry_at <= now_time,
            ),
        ]

        if aggregate_type is not None:
            conditions.append(OutboxEvents.aggregate_type == aggregate_type)

        if aggregate_id is not None:
            conditions.append(OutboxEvents.aggregate_id == aggregate_id)

        if event_type is not None:
            conditions.append(OutboxEvents.event_type == event_type)
            
        stmt = (
            select(OutboxEvents)
            .where(and_(*conditions))
            .order_by(OutboxEvents.id.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
            
        res = await self._db_session.execute(stmt)
        return list(res.scalars().all())


    async def mark_outbox_processing(
        self,
        *,
        event: OutboxEvents,
        updated_at: datetime,
    ) -> None:

        event.status = "PROCESSING"
        event.updated_at = updated_at
        await self._db_session.flush()


    async def mark_outbox_published(
        self,
        *,
        event: OutboxEvents,
        published_at: datetime,
    ) -> None:

        event.status = "PUBLISHED"
        event.published_at = published_at
        event.updated_at = published_at
        await self._db_session.flush()


    async def mark_outbox_retry(
        self,
        *,
        event: OutboxEvents,
        next_retry_at: datetime,
        last_error: str,
        updated_at: datetime,
    ) -> None:

        event.status = "PENDING"
        event.retry_count = int(event.retry_count) + 1
        event.next_retry_at = next_retry_at
        event.last_error = last_error[:2000]
        event.updated_at = updated_at
        await self._db_session.flush()


    async def mark_outbox_failed(
        self,
        *,
        event: OutboxEvents,
        last_error: str,
        updated_at: datetime,
    ) -> None:

        event.status = "FAILED"
        event.last_error = last_error[:2000]
        event.updated_at = updated_at
        await self._db_session.flush()



    
    async def commit(self) -> None:
        await self._db_session.commit()

    async def rollback(self) -> None:
        await self._db_session.rollback()
