
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.session import get_db
from app.domains.booking.services.booking_services import BookingService


def get_booking_service(
    db_session: AsyncSession = Depends(get_db),
) -> BookingService:
    return BookingService(db_session)