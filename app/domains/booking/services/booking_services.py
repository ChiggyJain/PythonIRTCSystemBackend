
from datetime import date, datetime, timedelta
import json
import httpx
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.utils.logger import app_logger
from app.core.exceptions import BaseAppException
from app.core.settings import get_settings
from app.common.utils.datetime import now_ist, today_ist
from app.common.repository.idempotency.sqlalchemy_repo import IdempotencySQLAlchemyRepository
from app.domains.booking.repository.sqlalchemy_repo import BookingSQLAlchemyRepository
from app.common.cache.redis_cache import acquireBookingSeatLocksThroughRedis


settings = get_settings()


class BookingService:

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
        seat_ids.sort()
        passengers = payload.get("passengers", "")
        IDEMPOTENCY_EVENT_TYPE = "BOOKING_CREATED"
        IDEMPOTENCY_EVENT_KEY_PREFIX = "BOOKING_CREATED"


        # checking given idempotency key exists or not
        event_key = f"{IDEMPOTENCY_EVENT_KEY_PREFIX}_{idempotency_key}"
        existing_idempotency_record = await self.idempotency_repo.get_idempotency_record_by_event_key(event_key)
        if existing_idempotency_record:
            return existing_idempotency_record.event_response
        
        # fetching schedule-inventory details
        inventoryScheduleDataObj = None
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://127.0.0.1:8000/schedules/{schedule_id}/availability")
            response.raise_for_status()
            data = response.json()
            inventoryScheduleDataObj = data.get("data", None)
        if inventoryScheduleDataObj == None:
            raise BaseAppException(
                status_code=400,
                messages=[f"No inventory schedules found for Train-Schedule-ID: {schedule_id}"],
            )
        if inventoryScheduleDataObj["status"]!="ACTIVE":
            raise BaseAppException(
                status_code=400,
                messages=[f"Inventory schedules is not active for Train-Schedule-ID: {schedule_id}"],
            )
        if inventoryScheduleDataObj["departure_date"]<today_ist():
            raise BaseAppException(
                status_code=400,
                messages=[f"Train is already departed for Train-Schedule-ID: {schedule_id}"],
            )
        
        # fetching seats data details
        seatDataList = None
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://127.0.0.1:8000/schedules/{schedule_id}/seats")
            response.raise_for_status()
            data = response.json()
            seatDataList = data.get("data", None)
        if seatDataList == None:
            raise BaseAppException(
                status_code=400,
                messages=[f"Seats details is not found for Train-Schedule-ID: {schedule_id}"],
            )

        # calculating seat price and availability details
        seatMap = {eachSeatDataObj["seat_id"] : eachSeatDataObj for eachSeatDataObj in seatDataList}
        bookingSeats = []
        totalAmount = 0
        for eachGivenSeatId in seat_ids:
            seat = seatMap.get(eachGivenSeatId, None)
            if seat == None:
                raise BaseAppException(
                    status_code=400,
                    messages=[f"Given Seat-ID: {eachGivenSeatId} is not in inventory schedule"],
                )
            is_seat_available = (
                seat["segmentStatus"] == "AVAILABLE"
                if (
                    from_station_sequence_number
                    and to_station_sequence_number
                    and seat.get("segmentStatus") is not None
                )
                else seat["status"] == "AVAILABLE"
            )
            if is_seat_available == False:
                raise BaseAppException(
                    status_code=400,
                    messages=[f"Seat: {seat["seat_number"]} is not available"],
                )
            if is_seat_available == True:
                bookingSeats.append(seat)
                totalAmount+= seat["price"]

   
        # preparing keys to acquire seat locks in redis via lua_script
        allRedisKeys = []
        for eachSeatId in seat_ids:
            key = f"booking:lock:seat:{schedule_id}:{eachSeatId}:{from_station_sequence_number}:{to_station_sequence_number}"
            allRedisKeys.append(key)
        curTimeStamp = int(datetime.now().timestamp())    
        redisKeyValue = f"pre-{curTimeStamp}:{curTimeStamp}"
        acquiredSeatLocksResponse = await acquireBookingSeatLocksThroughRedis(allRedisKeys, redisKeyValue, settings.BOOKING_TTL_SECONDS)
        if acquiredSeatLocksResponse.isSuccess == False:
            raise BaseAppException(
                status_code=400,
                messages=[f"One or more seats are being booked by another user. Please try again"],
            )
    
        try:
            
            curDateTime = now_ist()
            dt = datetime.strptime(curDateTime, "%Y-%m-%d %H:%M:%S")
            locked_expires_at = dt + timedelta(seconds=settings.LOCK_TTL_SECONDS)

            created_booking = await self.booking_repo.create_booking(
                user_id=user_id,
                schedule_id=schedule_id,
                train_id=inventoryScheduleDataObj["train_id"],
                train_number=inventoryScheduleDataObj["train_number"],
                train_name=inventoryScheduleDataObj["train_name"],
                departure_date=inventoryScheduleDataObj["departure_date"],
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






       