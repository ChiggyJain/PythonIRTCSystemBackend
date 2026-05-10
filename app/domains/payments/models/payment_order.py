
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


class PaymentOrders(Base):
    
    __tablename__ = "PAYMENT_ORDERS"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_idempotencyKey"),
        UniqueConstraint("payment_order_id", name="uq_paymentOrderId"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    booking_id: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0, server_default="0.00")
    currency: Mapped[str] = mapped_column(String(30), nullable=False, default="INR", server_default="INR")
    gateway_provider: Mapped[str] = mapped_column(String(30), nullable=False, default="razorpay", server_default="razorpay")
    gateway_order_id: Mapped[str] = mapped_column(String(255), nullable=True)
    gateway_payment_id: Mapped[str] = mapped_column(String(255), nullable=True)
    gateway_signature: Mapped[str] = mapped_column(String(255), nullable=True)
    failure_reason: Mapped[str] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
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
            "CREATED", "CAPTURED", "FAILED", 
            "REFUND_INITIATED", "REFUNDED", "PARTIALLY_REFUNDED",
            "FAILED", "CANCELLED", "EXPIRED", 
            name="status_enum"
        ),
        nullable=False,
        default="CREATED",
        server_default="CREATED",
    )