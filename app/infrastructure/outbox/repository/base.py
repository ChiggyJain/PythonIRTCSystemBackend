
"""
OutboxEvents Repository Base Interface
"""

from abc import (
    ABC, abstractmethod
)
from datetime import datetime
from typing import Any
from app.infrastructure.outbox.models.outbox_events_models import OutboxEvents


class OutboxEventsRepositoryBase(ABC):

    @abstractmethod
    async def add_outbox_event(
        self,
        *,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload_json: dict[str, Any],
        status: str,
    ) -> OutboxEvents:
        pass

    @abstractmethod
    async def fetch_pending_outbox_events(
        self,
        *,
        event_type: str,
        limit: int,
        now_time: datetime,
    ) -> list[OutboxEvents]:
        pass

    @abstractmethod
    async def mark_outbox_published(
        self,
        *,
        event: OutboxEvents,
        published_at: datetime,
    ) -> None:
        pass

    @abstractmethod
    async def mark_outbox_retry(
        self,
        *,
        event: OutboxEvents,
        next_retry_at: datetime,
        last_error: str,
        updated_at: datetime,
    ) -> None:
        pass

    @abstractmethod
    async def mark_outbox_failed(
        self,
        *,
        event: OutboxEvents,
        last_error: str,
        updated_at: datetime,
    ) -> None:
        pass

    
    
    @abstractmethod
    async def commit(self) -> None:
        pass

    @abstractmethod
    async def rollback(self) -> None:
        pass
