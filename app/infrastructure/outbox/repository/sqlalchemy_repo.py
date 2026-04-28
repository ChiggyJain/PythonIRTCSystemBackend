"""
OutboxEvents SQLAlchemy Repository
"""

from datetime import datetime
from typing import Any
from sqlalchemy import select, update, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.outbox.models.outbox_events_models import OutboxEvents
from app.infrastructure.outbox.repository.base import OutboxEventsRepositoryBase
from app.common.utils.datetime import now_ist


class OutboxEventsSQLAlchemyRepository(OutboxEventsRepositoryBase):

    def __init__(
        self,
        db: AsyncSession,
    ):
        self.db = db


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
        self.db.add(row)
        await self.db.flush()
        return row


    async def fetch_pending_outbox_events(
        self,
        *,
        event_type: str,
        limit: int,
        now_time: datetime,
    ) -> list[OutboxEvents]:

        stmt = (
            select(OutboxEvents)
            .where(
                OutboxEvents.event_type == event_type,
                OutboxEvents.status == "PENDING",
                or_(
                    OutboxEvents.next_retry_at.is_(None),
                    OutboxEvents.next_retry_at <= now_time,
                ),
            )
            .order_by(OutboxEvents.id.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())


    async def mark_outbox_published(
        self,
        *,
        event: OutboxEvents,
        published_at: datetime,
    ) -> None:

        event.status = "PUBLISHED"
        event.published_at = published_at
        event.updated_at = published_at
        await self.db.flush()


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
        await self.db.flush()


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
        await self.db.flush()



    
    async def commit(self) -> None:
        await self.db.commit()

    async def rollback(self) -> None:
        await self.db.rollback()
