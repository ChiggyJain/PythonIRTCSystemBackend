
from datetime import date
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.utils.logger import app_logger
from app.core.exceptions import BaseAppException
from app.domains.booking.repository.sqlalchemy_repo import BookingSQLAlchemyRepository


class BookingService:


    def __init__(self, db_session: AsyncSession):
        self.db = db_session
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



        pass