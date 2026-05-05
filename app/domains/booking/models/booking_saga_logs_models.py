
from datetime import datetime
from sqlalchemy import Integer, JSON, String, Date, Numeric, DateTime, Enum, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.common.utils.datetime import now_ist
from app.infrastructure.database.base import Base


class BookingSagaLogs(Base):
    
    __tablename__ = "BOOKING_SAGA_LOGS"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    booking_id: Mapped[int] = mapped_column(Integer, nullable=False)
    saga_step: Mapped[str] = mapped_column(
        Enum(
            "HOLD_SEATS", "CREATE_PAYMENT", "CONFIRM_SEATS", "COMPLETE", 
            name="saga_step_enum"
        ),
        nullable=False,
        default="HOLD_SEATS",
        server_default="HOLD_SEATS",
    )
    request: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    response: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str] = mapped_column(String(200), nullable=True)
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
        Enum(
            "PENDING", "COMPLETED", 
            "COMPENSATING", "COMPENSATED", "FAILED", 
            name="status_enum"
        ),
        nullable=False,
        default="PENDING",
        server_default="PENDING",
    )