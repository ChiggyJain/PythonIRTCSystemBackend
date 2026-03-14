"""
Users ORM Model
Rules:
------
- Table name = CAPITAL
- Column names = lowercase
- SQLAlchemy 2 style
- MySQL compatible
- Alembic compatible
- ENUM supported
- IST timezone supported
"""

from datetime import datetime
from sqlalchemy import (
    String, DateTime, Enum
)
from sqlalchemy.orm import (
    Mapped, mapped_column
)
from app.infrastructure.database.base import Base
from app.common.utils.datetime import now_ist


# =========================================================
# ENUMS
# =========================================================

gender_enum = Enum(
    "Male",
    "Female",
    "Transgender",
    name="gender_enum",
)

status_enum = Enum(
    "A",
    "Z",
    name="status_enum",
)


# =========================================================
# MODEL
# =========================================================

class Users(Base):
    """
    USERS table
    """

    __tablename__ = "USERS"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )

    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    mobile: Mapped[str] = mapped_column(
        String(15),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        unique=True,
    )

    password: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    gender: Mapped[str] = mapped_column(
        gender_enum,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_ist(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_ist(),
        onupdate=now_ist(),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        status_enum,
        nullable=False,
        default="A",
    )