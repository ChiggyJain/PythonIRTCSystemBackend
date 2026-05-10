
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
        self.db = db_session
        self.idempotency_repo = IdempotencySQLAlchemyRepository(db_session)
        self.booking_repo = BookingSQLAlchemyRepository(db_session)
        


    async def create_booking_details(self, *, payload: dict) -> dict:
        
        try:

            # extracted parameters
            user_id = int(payload.get("user_id", 0))
            idempotency_key = payload.get("idempotency_key", "")
            schedule_id = int(payload.get("schedule_id", 0))
            from_station_id = int(payload.get("from_station_id", 0))
            to_station_id = int(payload.get("to_station_id", 0))
            from_station_sequence_number = int(payload.get("from_station_sequence_number", 0))
            to_station_sequence_number = int(payload.get("to_station_sequence_number", 0))
            seat_ids = payload.get("seat_ids", [])
            seat_ids.sort()
            passengers = payload.get("passengers", [])
            booking_details = {}
            IDEMPOTENCY_EVENT_TYPE = "booking"
            IDEMPOTENCY_EVENT_KEY_PREFIX = "booking"

            # checking given idempotency key exists or not
            event_key = f"{IDEMPOTENCY_EVENT_KEY_PREFIX}:{idempotency_key}"
            existing_idempotency_record = await self.idempotency_repo.get_idempotency_record_by_event_key(event_key)
            if existing_idempotency_record:
                return standardize_response(
                    status_code=200,
                    messages=[f"Booking created successfully"],
                    data=None,
                )
            
            # fetching schedule availability from external inventory service
            inventoryScheduleDataObj = None
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{settings.INVENTORY_SERVICE_BASE_URL}/inventory/schedules/{schedule_id}/availability")
                response.raise_for_status()
                data = response.json()
                inventoryScheduleDataObj = data.get("data", None)
            print(f"inventoryScheduleDataObj: {inventoryScheduleDataObj}")
            if inventoryScheduleDataObj == None:
                return standardize_response(
                    status_code=404,
                    messages=[f"No inventory schedule found for Train-Schedule-ID: {schedule_id}"],
                )
            if inventoryScheduleDataObj["status"]!="ACTIVE":
                return standardize_response(
                    status_code=404,
                    messages=[f"Inventory schedule not active for Train-Schedule-ID: {schedule_id}"],
                )
            departure_date = datetime.strptime(inventoryScheduleDataObj["departure_date"], "%Y-%m-%d").date()
            if departure_date<today_ist():
                return standardize_response(
                    status_code=404,
                    messages=[f"Train already departed for Train-Schedule-ID: {schedule_id}"],
                )
            
            # fetching seats details from external inventory service
            seatData = None
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{settings.INVENTORY_SERVICE_BASE_URL}/inventory/schedules/{schedule_id}/seats", params={
                    "from_station_sequence_number" : from_station_sequence_number,
                    "to_station_sequence_number" : to_station_sequence_number
                })
                response.raise_for_status()
                data = response.json()
                seatData = data.get("data", None)
            print(f"seatData: {seatData}")
            if seatData == None:
                return standardize_response(
                    status_code=404,
                    messages=[f"Seats details not found for Train-Schedule-ID: {schedule_id}"],
                )

            # verify all requested seats exist and are available
            # calculating seat price and availability details
            seatMap = {eachSeatDataObj["seat_id"] : eachSeatDataObj for eachSeatDataObj in seatData["seats"]}
            bookingSeats = []
            totalAmount = 0
            for eachGivenSeatId in seat_ids:
                seat = seatMap.get(eachGivenSeatId, None)
                if seat == None:
                    return standardize_response(
                        status_code=404,
                        messages=[f"Given Seat-ID: {eachGivenSeatId} not found in schedule"],
                    )
                is_seat_available = (
                    seat["segment_status"] == "AVAILABLE"
                    if (
                        from_station_sequence_number
                        and to_station_sequence_number
                        and seat.get("segment_status") is not None
                    )
                    else seat["status"] == "AVAILABLE"
                )
                if is_seat_available == False:
                    return standardize_response(
                        status_code=400,
                        messages=[f"Seat-Number: {seat["seat_number"]} is not available"],
                    )
                if is_seat_available == True:
                    bookingSeats.append(seat)
                    totalAmount+= seat["price"]

            
            print(f"totalAmount: {totalAmount}")
            return standardize_response(
                status_code=200,
                messages=[f"Booking created: {totalAmount}"],
            )
        
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
            booking_details = orm_to_dict(created_booking)
            bookingId = created_booking.id
            created_booking_seats = await self.booking_repo.create_booking_seats(booking_id=bookingId, seat_details=bookingSeats)
            booking_details["seats"] = [
                orm_to_dict(seat)
                for seat in created_booking_seats
            ]
            created_booking_passengers = await self.booking_repo.create_booking_passengers(booking_id=bookingId, passenger_details=passengers)
            booking_details["passengers"] = [
                orm_to_dict(passenger)
                for passenger in created_booking_passengers
            ]

            # execute saga step1: Hold seats in inventory
            await executeHoldSeats(
                booking_details, seat_ids, settings.LOCK_TTL_SECONDS,
                from_station_sequence_number, to_station_sequence_number
            )

            # execute saga step2: Create payment order
            createdPaymentOrderData = await executeCreatePayment(booking_details)

            # refreshing the booking-details
            booking_details["payment_order_id"] = createdPaymentOrderData["payment_order_id"]
            booking_details["status"] = "PAYMENT_PENDING"
            booking_details["payment_order"] = {
                "payment_order_id" : createdPaymentOrderData["payment_order_id"],
                "gateway_order_id" : createdPaymentOrderData["gateway_order_id"],
                "total_amount" : createdPaymentOrderData["total_amount"],
                "currency" : createdPaymentOrderData["currency"],
                "key_id" : createdPaymentOrderData["key_id"],
            }

            # storing idempotency-key details
            await self.idempotency_repo.add_idempotency_record(
                event_key = event_key,
                event_type = IDEMPOTENCY_EVENT_TYPE,
                event_response = booking_details
            )

            return booking_details
        
        except Exception:

            if booking_details:
                await compensateAll(booking_details, seat_ids)
                isBookingRecordUpdated = await self.booking_repo.update_booking_details(
                    where_data={
                        "booking_id": booking_details["id"],
                    },
                    update_data = {
                        "failure_reason" : "Fail to create booking details",
                        "status" : "FAILED"
                    }
                )
                releasedSeatLocksResponse = await releaseBookingSeatLocksThroughRedis(allRedisKeys, redisKeyValue)
                

            raise BaseAppException(
                status_code=400,
                messages=["Unable to create booking"],
            )






       