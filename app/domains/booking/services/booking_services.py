
from datetime import date, datetime, timedelta
import json
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.utils.logger import app_logger
from app.core.exceptions import BaseAppException
from app.core.settings import get_settings
from app.common.utils.datetime import now_ist
from app.common.repository.idempotency.sqlalchemy_repo import IdempotencySQLAlchemyRepository
from app.domains.booking.repository.sqlalchemy_repo import BookingSQLAlchemyRepository
from app.common.cache.redis_cache import acquireBookingSeatLocksThroughRedis


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

        
        # preparing keys to acquire seat locks in redis via lua_script
        allRedisKeys = []
        for eachSeatId in seat_ids:
            key = f"booking:lock:seat:{schedule_id}:{eachSeatId}:{from_station_sequence_number}:{to_station_sequence_number}"
            allRedisKeys.append(key)
        curTimeStamp = int(datetime.now().timestamp())    
        redisKeyValue = f"pre-{curTimeStamp}:{curTimeStamp}"
        acquiredSeatLocksResponse = await acquireBookingSeatLocksThroughRedis(allRedisKeys, redisKeyValue, settings.BOOKING_TTL_SECONDS)
        print(f"acquiredSeatLocksResponse: {acquiredSeatLocksResponse}")

        if acquiredSeatLocksResponse.isSuccess == False:
            raise BaseAppException(
                status_code=400,
                messages=[f"One or more seats are being booked by another user. Please try again"],
            )
        
        try:
            
            curDateTime = now_ist()
            dt = datetime.strptime(curDateTime, "%Y-%m-%d %H:%M:%S")
            locked_expires_at = dt + timedelta(minutes=10)

            created_booking = await self.booking_repo.create_booking(
                user_id=user_id,
                schedule_id=schedule_id,
                train_id="",
                train_number="",
                train_name="",
                departure_date="",
                total_amount=totalAmount,
                seat_count=len(seat_ids),
                from_station_id=from_station_id,
                to_station_id=to_station_id,
                from_station_sequence_number=from_station_sequence_number,
                to_station_sequence_number=to_station_sequence_number,
                idempotency_key=idempotency_key,
                payment_order_id=None,
                locked_expires_at=locked_expires_at,
                failure_reason=None,
                version=0,
                status="PENDING",
            )
            bookingId = created_booking.id            
            created_booking_seats = await self.booking_repo.create_booking_seats(booking_id=bookingId, seat_details=bookingSeats)
            created_booking_passengers = await self.booking_repo.create_booking_passengers(booking_id=bookingId, passenger_details=passengers)
            created_booking_saga_logs = await self.booking_repo.create_booking_saga_logs(
                booking_id=bookingId, 
                saga_step="HOLD_SEATS", 
                request={
                    "user_id":user_id, "schedule_id":schedule_id, "seat_ids":seat_ids, "ttlSeconds" : settings.LOCK_TTL_SECONDS,
                    "from_station_sequence_number":from_station_sequence_number, "to_station_sequence_number":to_station_sequence_number                     
                },
                response=None, 
                error=None, 
                status="PENDING"
            )


        except Exception:
            await self._db_session.rollback()
            raise BaseAppException(
                status_code=400,
                messages=["Unable to create booking"],
            )






       