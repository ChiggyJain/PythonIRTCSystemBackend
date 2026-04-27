
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
    
    """
    OTP_CHALLENGES
    Stores one OTP challenge per request (password change, email verify, mobile verify).
    Why this table exists:
    - Track OTP lifecycle in DB (requested/sent/verified/expired/blocked).
    - Keep OTP verification secure (hash for compare, ciphertext for async dispatch workers).
    - Support retries, expiry, and attempt limits in a production-safe way.
    """

    __tablename__ = "OTP_CHALLENGES"
    __table_args__ = (
        UniqueConstraint("challenge_id", name="uq_otp_challenges_challenge_id"),
        Index("ix_otp_challenges_user_purpose_status", "user_id", "purpose", "status"),
        Index("ix_otp_challenges_expires_at", "expires_at"),
    )

    # Auto-increment primary key (project DB convention).
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )

    # Public unique reference returned to client and used in confirm API.
    # Example: PWDCHG_101_20260316094500_A1B2C3
    challenge_id: Mapped[str] = mapped_column(String(80), nullable=False)
    
    # Owner of this OTP challenge.
    # No DB foreign key as per project policy; relation handled in service layer.
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Business reason of OTP.
    # Example values: PASSWORD_CHANGE, EMAIL_VERIFY, MOBILE_VERIFY
    purpose: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # OTP channel requested by user.
    # Example values: EMAIL, MOBILE 
    channel: Mapped[str] = mapped_column(String(20), nullable=False)  
    
    # Safe-to-log/display destination format.
    # Example: c***g@gmail.com or 98******10
    destination_masked: Mapped[str] = mapped_column(String(120), nullable=False)
    
    # HMAC/hash of OTP used at verify time.
    # Never store plain OTP.
    otp_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Encrypted OTP used by async dispatcher/consumer to send actual OTP.
    # Kafka payload can carry challenge_id only, then worker decrypts from DB.
    otp_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)

    # Key version for future key rotation compatibility.
    cipher_key_version: Mapped[str] = mapped_column(String(50), nullable=False)

    # OTP validity end time.
    # Confirm API must reject if current time > expires_at.
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Max OTP tries allowed before block.
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=5)

    # Number of consumed attempts.
    # Incremented on each failed verify (and optionally on success depending policy).
    attempts_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Last technical/business failure reason.
    # Example: OTP_INVALID, OTP_EXPIRED, DISPATCH_FAILED
    last_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Encrypted JSON metadata for flow-specific context.
    # For EMAIL_CHANGE purpose, example decrypted JSON:
    # {
    #   "old_email": "old@example.com",
    #   "new_email": "new@example.com"
    # }
    # Stored encrypted as text only.
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Audit timestamps (IST utility in project).    
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

    # Current lifecycle status.
    # Typical values: REQUESTED, SENT, VERIFIED, EXPIRED, BLOCKED, DISPATCH_FAILED
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="REQUESTED")



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



class SecurityEventLog(Base):

    """
    SECURITY_EVENT_LOG
    Unified audit log for security-related actions.
    Why this table exists:
    - Keep a single timeline for OTP + account security events.
    - Help debugging, support, compliance, and incident analysis.
    - Track what happened, for whom, via which channel/provider, and with what result.
    Example events:
    - otp_requested
    - otp_dispatched
    - otp_dispatch_failed
    - otp_verified
    - otp_verification_failed
    - password_changed
    - email_verified
    - mobile_verified
    """

    __tablename__ = "SECURITY_EVENT_LOG"
    __table_args__ = (
        Index("ix_security_event_user_created", "user_id", "created_at"),
        Index("ix_security_event_name_created", "event_name", "created_at"),
        Index("ix_security_event_correlation_id", "correlation_id"),
    )

    # Auto-increment primary key (project DB convention).
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )

    # User related to this event.
    # No DB foreign key as per project policy.
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Event name (business action).
    # Example: otp_requested, password_changed
    event_name: Mapped[str] = mapped_column(String(80), nullable=False)
    
    # Broad event group for filtering/reporting.
    # Example: OTP, ACCOUNT_SECURITY, EMAIL_VERIFICATION, OUTBOX
    event_category: Mapped[str] = mapped_column(String(60), nullable=False)
    
    # Delivery/verification channel if applicable.
    # Example: EMAIL, MOBILE, or None
    channel: Mapped[str | None] = mapped_column(String(20), nullable=True)
    
    # Provider used for external action.
    # Example: SENDGRID, MSG91, TWILIO, KAFKA, or None
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Machine-readable reason for failures or special states.
    # Example: OTP_INVALID, OTP_EXPIRED, DISPATCH_FAILED
    reason_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Correlation id to trace one flow across API/outbox/kafka/consumer.
    correlation_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Request id from incoming API layer (if available).
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Client IP captured at API boundary (if available).
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Client user-agent captured at API boundary (if available).
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Extra event-specific details in JSON.
    # Example: challenge_id, provider_message_id, retry_count
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Event creation timestamp (append-only log style).
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_ist,
    )

    # Result state for this event.
    # Example: accepted, sent, verified, failed, rejected, expired, success
    status: Mapped[str] = mapped_column(String(30), nullable=False)