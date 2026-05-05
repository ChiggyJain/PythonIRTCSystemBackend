
from datetime import date
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.utils.logger import app_logger
from app.core.exceptions import BaseAppException
from app.core.settings import get_settings
from app.common.repository.idempotency.sqlalchemy_repo import IdempotencySQLAlchemyRepository
from app.domains.booking.repository.sqlalchemy_repo import BookingSQLAlchemyRepository

settings = get_settings()

class BookingService:


    IDEMPOTENCY_EVENT_TYPE = "BOOKING_CREATED"
    IDEMPOTENCY_EVENT_KEY_PREFIX = "BOOKING_CREATED"

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.idempotency_repo = IdempotencySQLAlchemyRepository(db_session)
        self.booking_repo = BookingSQLAlchemyRepository(db_session)
        


    async def create_booking_details(self, *, payload: dict) -> dict:
        
        # extracted parameters
        user_id = int(payload.get("user_id", 0))
        idempotency_key = payload.get("idempotency_key", "")
        schedule_id = int(payload.get("schedule_id", 0))
        from_station_id = int(payload.get("from_station_id", 0))
        to_station_id = int(payload.get("to_station_id", 0))
        from_station_sequence_number = int(payload.get("from_station_sequence_number", 0))
        to_station_sequence_number = int(payload.get("to_station_sequence_number", 0))
        seat_ids = payload.get("seat_ids", "")
        passengers = payload.get("passengers", "")

        # checking given idempotency key exists or not
        event_key = f"{self.IDEMPOTENCY_EVENT_KEY_PREFIX}_{idempotency_key}"
        existing_idempotency_record = await self.idempotency_repo.get_idempotency_record_by_event_key(event_key)
        if existing_idempotency_record:
            return existing_idempotency_record
        
        # availability = getAvailability(schedule_id) via internal http-call through inventory_service
        # check availability.status!="A"
            # throw error
        # check availability.departure_date<curDate
            # throw error

        
        # seatData = getSeats(schedule_id, from_station_sequence_number, to_station_sequence_number) via internal http-call through inventory_service
        # seatMap = store seatData{seatId, seatObject}

        bookingSeats = []
        totalAmount = 0
        
        """
        for eachSeatId in seat_ids:
            seat = seatMap.get(eachSeatId, None)
            if !seat:
                throw error
            isSeatAvailable = (from_station_sequence_number and to_station_sequence_number and seat.segementStatus!=undefined)
                ? seat.segementStatus === "AVAILABLE"
                : seat.status === "AVAILABLE"
            if isSeatAvailable == False:
                throw error
            bookingSeats.append(seat)
            totalAmount+= seat.price
        """

        sortedSeatIds = seat_ids
        
        acquired_lockValue = await self.acquireSeatLocks(
            schedule_id,
            sortedSeatIds,
            f"pre-${'PutHereCurDateTimeStamp'}",
            settings.BOOKING_TTL_SECONDS,
            from_station_sequence_number,
            to_station_sequence_number
        )



        pass











