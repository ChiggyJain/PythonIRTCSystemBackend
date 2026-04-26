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

mobile_verified_enum = Enum(
    "Y",
    "N",
    name="mobile_verified_enum",
)

email_verified_enum = Enum(
    "Y",
    "N",
    name="email_verified_enum",
)

gender_enum = Enum(
    "Male",
    "Female",
    "Transgender",
    name="gender_enum",
)

profile_enum = Enum(
    "User",
    "Admin",
    "Guest",
    name="profile_enum",
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

    # Mobile verification flag used by frontend to show "Verify Mobile" button.
    # Example:
    # Y = verified
    # N = not verified
    is_mobile_verified: Mapped[str] = mapped_column(
        mobile_verified_enum,
        nullable=False,
        default="N",
    )

    # Last successful mobile verification timestamp in IST.
    # Example:
    # 2026-03-17 20:45:10+05:30
    mobile_verified_last_datetime: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    email: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        unique=True,
    )

    # Email verification flag used by frontend to show "Verify Email" button.
    # Example:
    # Y = verified
    # N = not verified
    is_email_verified: Mapped[str] = mapped_column(
        email_verified_enum,
        nullable=False,
        default="N",
    )

    # Last successful email verification timestamp in IST.
    # Example:
    # 2026-03-17 20:45:10+05:30
    email_verified_last_datetime: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    password: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    gender: Mapped[str] = mapped_column(
        gender_enum,
        nullable=False,
    )

    profile: Mapped[str] = mapped_column(
        profile_enum,
        nullable=False,
        default="User",
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