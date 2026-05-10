
from datetime import datetime
from sqlalchemy import (
    Integer, String, Date, 
    Numeric, DateTime, Enum, 
    func, UniqueConstraint,
    JSON
)
from sqlalchemy.orm import Mapped, mapped_column
from app.common.utils.datetime import now_ist
from app.infrastructure.database.base import Base


class PaymentAuditLogs(Base):
    
    __tablename__ = "PAYMENT_AUDIT_LOGS"
    __table_args__ = (
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    payment_order_id: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    gateway_response: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
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
            "A", "Z",
            name="status_enum"
        ),
        nullable=False,
        default="A",
        server_default="A",
    )