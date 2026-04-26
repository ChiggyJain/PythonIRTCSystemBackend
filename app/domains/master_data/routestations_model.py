
from datetime import datetime, time
from fastapi.datastructures import Default
from sqlalchemy import (
    String,
    DateTime,
    Integer,
    UniqueConstraint,
    Index,
    Enum,
    Time
)
from sqlalchemy.orm import Mapped, mapped_column
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


class RouteStations(Base):

    """
    ROUTE_STATIONS table
    """

    __tablename__ = "ROUTE_STATIONS"
    
    __table_args__ = (
        UniqueConstraint("route_id", "sequence_number", name="uq_routeId_seqNumber"),
        UniqueConstraint("route_id", "station_id", name="uq_routeId_stationId"),
        Index("ix_status", "status"),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )
    # this route_id column is the primary key of ROUTE table model only but I don't want to treat as foreign-key concept
    route_id: Mapped[int] = mapped_column(nullable=False)
    # this station_id column is the primary key of STATION table model only but I don't want to treat as foreign-key concept
    station_id: Mapped[int] = mapped_column(nullable=False)
    # order of station in route like 1,2,3,4,5,6 etc
    sequence_number: Mapped[int] = mapped_column(nullable=False)
    arrival_time: Mapped[time] = mapped_column(Time, nullable=False)
    departure_time: Mapped[time] = mapped_column(Time, nullable=False)
    distance_from_origin: Mapped[float] = mapped_column(nullable=False, default=0)
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
