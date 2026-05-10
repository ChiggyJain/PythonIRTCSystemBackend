
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


class RefundOrders(Base):
    
    __tablename__ = "REFUND_ORDERS"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_idempotencyKey"),
        UniqueConstraint("gateway_refund_id", name="uq_gatewayRefundId"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    payment_order_id: Mapped[int] = mapped_column(Integer, nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0, server_default="0.00")
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    gateway_refund_id: Mapped[str] = mapped_column(String(255), nullable=True)
    failure_reason: Mapped[str] = mapped_column(String(255), nullable=True)
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
            "INITIATED", "PROCESSING", "COMPLETED", 
            "FAILED", "CANCELLED", "EXPIRED", 
            name="status_enum"
        ),
        nullable=False,
        default="INITIATED",
        server_default="INITIATED",
    )