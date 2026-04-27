"""
Auth models
USER_TOKENS table
"""

from datetime import datetime
from sqlalchemy import (
    String, DateTime, Enum, Boolean, Index
)
from sqlalchemy.orm import (
    Mapped, mapped_column
)
from app.infrastructure.database.base import Base
from app.common.utils.datetime import now_ist


# =========================================================
# ENUMS
# =========================================================

status_enum = Enum(
    "A",
    "Z",
    name="status_enum",
)


# =========================
# USER_TOKENS
# =========================

class UserTokens(Base):

    __tablename__ = "USER_TOKENS"
    __table_args__ = (
        Index("ix_user_tokens_user_status_revoked", "user_id", "status", "revoked"),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )

    user_id: Mapped[int] = mapped_column(
        nullable=False,
    )

    token_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    token_hash: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    ip_address: Mapped[str] = mapped_column(
        String(100),
        nullable=True,
    )

    user_agent: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_ist,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_ist,
        onupdate=now_ist,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        status_enum,
        nullable=False,
        default="A",
    )