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
from zoneinfo import ZoneInfo

from sqlalchemy import String, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


# =========================================================
# IST TIMEZONE
# =========================================================

IST = ZoneInfo("Asia/Kolkata")


def get_ist_time() -> datetime:
    """
    Return current IST datetime
    """
    return datetime.now(IST)


# =========================================================
# ENUMS
# =========================================================

gender_enum = Enum(
    "Male",
    "Female",
    "Transgender",
    "Others",
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

    # -------------------------
    # id (PK)
    # -------------------------

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )

    # -------------------------
    # first_name
    # -------------------------

    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # -------------------------
    # last_name
    # -------------------------

    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # -------------------------
    # mobile (15 digits max)
    # -------------------------

    mobile: Mapped[str] = mapped_column(
        String(15),
        nullable=False,
    )

    # -------------------------
    # email
    # -------------------------

    email: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        unique=True,
    )

    # -------------------------
    # password
    # -------------------------

    password: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    # -------------------------
    # gender ENUM
    # -------------------------

    gender: Mapped[str] = mapped_column(
        gender_enum,
        nullable=False,
    )

    # -------------------------
    # created_at (IST)
    # only on insert
    # -------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=get_ist_time(),
        nullable=False,
    )

    # -------------------------
    # updated_at (IST)
    # on insert + update
    # -------------------------

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=get_ist_time(),
        onupdate=get_ist_time(),
        nullable=False,
    )

    # -------------------------
    # status ENUM
    # default A
    # -------------------------

    status: Mapped[str] = mapped_column(
        status_enum,
        nullable=False,
        default="A",
    )