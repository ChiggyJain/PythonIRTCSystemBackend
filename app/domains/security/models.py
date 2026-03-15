
"""
Security domain models:
- OTP_CHALLENGES
- OUTBOX_EVENTS
- SECURITY_EVENT_LOG
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


class OtpChallenges(Base):

    __tablename__ = "OTP_CHALLENGES"
    __table_args__ = (
        UniqueConstraint("challenge_id", name="uq_otp_challenges_challenge_id"),
        Index("ix_otp_challenges_user_purpose_status", "user_id", "purpose", "status"),
        Index("ix_otp_challenges_expires_at", "expires_at"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )
    challenge_id: Mapped[str] = mapped_column(String(80), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    # PASSWORD_CHANGE / EMAIL_VERIFY / MOBILE_VERIFY
    purpose: Mapped[str] = mapped_column(String(50), nullable=False)
    # EMAIL / MOBILE  
    channel: Mapped[str] = mapped_column(String(20), nullable=False)  
    destination_masked: Mapped[str] = mapped_column(String(120), nullable=False)
    otp_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    otp_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    cipher_key_version: Mapped[str] = mapped_column(String(50), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    attempts_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_ist(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_ist(),
        onupdate=now_ist(),
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="REQUESTED")



class OutboxEvents(Base):

    __tablename__ = "OUTBOX_EVENTS"
    __table_args__ = (
        Index("ix_outbox_events_status_next_retry", "status", "next_retry_at"),
        Index("ix_outbox_events_created_at", "created_at"),
        UniqueConstraint("event_type", "aggregate_id", name="uq_outbox_event_aggregate"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )
    aggregate_type: Mapped[str] = mapped_column(String(50), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(100), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_ist(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_ist(),
        onupdate=now_ist(),
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")



class SecurityEventLog(Base):

    __tablename__ = "SECURITY_EVENT_LOG"
    __table_args__ = (
        Index("ix_security_event_user_created", "user_id", "created_at"),
        Index("ix_security_event_name_created", "event_name", "created_at"),
        Index("ix_security_event_correlation_id", "correlation_id"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    event_name: Mapped[str] = mapped_column(String(80), nullable=False)
    event_category: Mapped[str] = mapped_column(String(60), nullable=False)
    channel: Mapped[str | None] = mapped_column(String(20), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reason_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_ist,
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False)