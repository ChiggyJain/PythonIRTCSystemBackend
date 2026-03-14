"""
Auth models

USER_TOKENS table
"""

from sqlalchemy import (
    Integer,
    String,
    DateTime,
    Boolean,
    Enum,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database.base import Base



# =========================
# USER_TOKENS
# =========================

class UserTokens(Base):

    __tablename__ = "USER_TOKENS"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    token: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    token_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    expires_at: Mapped = mapped_column(
        DateTime,
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

    created_at: Mapped = mapped_column(
        DateTime,
        nullable=False,
    )

    updated_at: Mapped = mapped_column(
        DateTime,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(1),
        default="A",
        nullable=False,
    )