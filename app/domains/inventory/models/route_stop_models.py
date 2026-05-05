
from datetime import datetime
from sqlalchemy import Integer, String, UniqueConstraint, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column
from app.common.utils.datetime import now_ist
from app.infrastructure.database.base import Base


class RouteStop(Base):

    __tablename__ = "ROUTE_STOP"
    __table_args__ = (
        UniqueConstraint("schedule_id", "station_id", name="uq_scheduleIdStationId"),
        UniqueConstraint("schedule_id", "sequence_number", name="uq_scheduleIdSequenceNumber"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    schedule_id: Mapped[int] = mapped_column(Integer, nullable=False)
    station_id: Mapped[int] = mapped_column(Integer, nullable=False)
    station_name: Mapped[str] = mapped_column(String(150), nullable=False)
    station_code: Mapped[str] = mapped_column(String(20), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
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
        Enum("ACTIVE", "INACTIVE", name="route_stop_status"),
        nullable=False,
        default="ACTIVE",
        server_default="ACTIVE",
    )