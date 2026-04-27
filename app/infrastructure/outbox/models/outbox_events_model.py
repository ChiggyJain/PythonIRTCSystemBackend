
"""
OUTBOX_EVENTS
"""

from datetime import datetime
from sqlalchemy import (
    String,
    DateTime,
    Text,
    Integer,
    JSON,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database.base import Base
from app.common.utils.datetime import now_ist


class OutboxEvents(Base):

    """
    OUTBOX_EVENTS
    Reliable event queue stored in MySQL for async processing.
    Why this table exists:
    - API should return fast (202) without waiting for Kafka/provider.
    - Avoid DB+Kafka dual-write data loss problem.
    - If Kafka is down, events remain in DB and workers retry later.
    Typical flow:
    1) API writes business row + outbox row in same DB transaction.
    2) Publisher worker reads pending outbox rows.
    3) Worker publishes event to Kafka.
    4) Row marked PUBLISHED (or retry/failed based on result).
    """

    __tablename__ = "OUTBOX_EVENTS"
    __table_args__ = (
        Index("ix_outbox_events_status_next_retry", "status", "next_retry_at"),
        Index("ix_outbox_events_created_at", "created_at"),
        UniqueConstraint("event_type", "aggregate_id", name="uq_outbox_event_aggregate"),
    )

    # Auto-increment primary key (project DB convention).
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )

    # Logical aggregate/domain this event belongs to.
    # Example: OTP_CHALLENGE, USER_SECURITY, PROFILE
    aggregate_type: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Business entity id/reference for the aggregate.
    # Example: PWDCHG_101_20260316094500_A1B2C3
    aggregate_id: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Event name/version used by workers and Kafka routing.
    # Example: PWDCHANGED_OTP_DISPATCH_REQUESTED_V1
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    
    # Event body (JSON) required by downstream workers/consumers.
    # Example keys: challenge_id, user_id, purpose, channel, destination
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    # How many publish attempts happened so far.
    # Increment on each failed publish attempt.
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Next eligible retry time (for backoff logic).
    # Null means eligible immediately.
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Last publish failure details (trimmed).
    # Example: broker timeout, topic unavailable, serialization error
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Time when event was successfully published to Kafka.
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Audit timestamps.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_ist,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_ist,
        onupdate=now_ist,
    )

    # Current publishing state.
    # Typical values: PENDING, PUBLISHED, FAILED
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")

