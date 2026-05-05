
from datetime import date
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.utils.logger import app_logger
from app.core.exceptions import BaseAppException
from app.common.repository.idempotency.sqlalchemy_repo import IdempotencySQLAlchemyRepository
from app.domains.booking.repository.sqlalchemy_repo import BookingSQLAlchemyRepository


class BookingService:


    IDEMPOTENCY_EVENT_TYPE = "BOOKING_CREATED"
    IDEMPOTENCY_EVENT_KEY_PREFIX = "BOOKING_CREATED"

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.idempotency_repo = IdempotencySQLAlchemyRepository(db_session)
        self.booking_repo = BookingSQLAlchemyRepository(db_session)
        


    async def create_booking_details(self, *, payload: dict) -> dict:
        
        user_id = 0
        idempotency_key = int(payload.get("idempotency_key", 0))
        schedule_id = int(payload.get("schedule_id", 0))
        from_station_id = int(payload.get("from_station_id", 0))
        to_station_id = int(payload.get("to_station_id", 0))
        from_station_sequence_number = int(payload.get("from_station_sequence_number", 0))
        to_station_sequence_number = int(payload.get("to_station_sequence_number", 0))
        seat_ids = int(payload.get("seat_ids", ""))
        passengers = int(payload.get("passengers", ""))

        event_key = f"{self.IDEMPOTENCY_EVENT_KEY_PREFIX}_{idempotency_key}"
        existing = await self.idempotency_repo.get_idempotency_record_by_event_key(event_key)
        if existing:
            return {
                "status": "duplicate",
                "event_key": event_key,
                "schedule_id": schedule_id,
                "message": "Event already processed",
            }
        

        pass