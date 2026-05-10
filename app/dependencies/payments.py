
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.session import get_db
from app.domains.payments.services.payment_services import PaymentService


def get_payment_service(
    db_session: AsyncSession = Depends(get_db),
) -> PaymentService:
    return PaymentService(db_session)