
from datetime import date, datetime, timedelta
import json
import httpx
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import BaseAppException
from app.core.response import (
    standardize_response, 
)
from app.core.settings import get_settings
from app.common.utils.datetime import now_ist, today_ist
from app.common.utils.orm_to_dict import orm_to_dict
from app.common.repository.idempotency.sqlalchemy_repo import IdempotencySQLAlchemyRepository
from app.domains.booking.repository.sqlalchemy_repo import BookingSQLAlchemyRepository
from app.common.cache.redis_cache import (
    acquireBookingSeatLocksThroughRedis,
    releaseBookingSeatLocksThroughRedis
)
from app.services.saga_services import (
    executeHoldSeats,
    executeCreatePayment,
    compensateAll
)


settings = get_settings()



class BookingService:

    def __init__(self, db_session: AsyncSession):
        self._db_session = db_session
        self.idempotency_repo = IdempotencySQLAlchemyRepository(db_session)
        self.booking_repo = BookingSQLAlchemyRepository(db_session)
        


    async def create_booking_details(self, *, payload: dict) -> dict:
        
        try:

            pass

        except Exception as e:

            pass