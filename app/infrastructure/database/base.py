
"""
SQLAlchemy Declarative Base
This module defines the Base class for all ORM models.
All domain models must inherit from this Base.
Why separate file?
------------------
- Needed by Alembic
- Needed by SQLAlchemy metadata
- Avoid circular imports
- Support multi-domain models
- Production safe design
This Base does NOT create tables.
It only stores metadata.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Base class for all ORM models.
    Example:
        class User(Base):
            __tablename__ = "users"
    """

    pass