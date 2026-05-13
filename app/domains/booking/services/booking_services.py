
from datetime import date, datetime, timedelta
from decimal import Decimal
import json
import sched
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
from app.common.cache.redis_cache import (
    acquireBookingSeatLocksThroughRedis,
    forceReleaseSeatLocksThroughRedis,
    releaseBookingSeatLocksThroughRedis
)
from app.common.repository.idempotency.sqlalchemy_repo import IdempotencySQLAlchemyRepository
from app.domains.booking.models.booking_passgenger_models import BookingPassengers
from app.domains.booking.models.booking_seats_models import BookingSeats
from app.domains.booking.repository.sqlalchemy_repo import BookingSQLAlchemyRepository
from app.domains.booking.models.bookings_models import Bookings
from app.domains.booking.models.booking_saga_logs_models import BookingSagaLogs
from app.infrastructure.outbox.repository.sqlalchemy_repo import OutboxEventsSQLAlchemyRepository
from app.domains.users.repository.sqlalchemy_repo import UsersSQLAlchemyRepository


settings = get_settings()



class BookingService:

    def __init__(self, db_session: AsyncSession):
        self._db_session = db_session
        self.idempotency_repo = IdempotencySQLAlchemyRepository(db_session)
        self.booking_repo = BookingSQLAlchemyRepository(db_session)
        self.outbox_repo = OutboxEventsSQLAlchemyRepository(db_session)
        self.user_repo = UsersSQLAlchemyRepository(db_session)


    async def compensateAll(self, *, payload: dict) -> dict:
        
        try:
            
            # extracted parameters
            booking_id = int(payload.get("booking_id", 0))
            seat_ids = payload.get("seat_ids", [])
            seat_ids.sort()

            if booking_id <= 0 or not seat_ids:
                return standardize_response(
                    status_code=400,
                    messages=[f"Invalid parameters are passed for booking compensation steps"]
                )

            if booking_id>0 and len(seat_ids)>0:
                
                # fetching booking details
                booking_list = await self.booking_repo.get_booking_details(
                    where_conditions = [
                        Bookings.id == booking_id,
                    ],
                    order_by = [
                        Bookings.id.asc()
                    ]
                )
                if not booking_list:
                    return standardize_response(
                        status_code=404,
                        messages=[f"Booking details not found for compensating"]
                    )
                
                if booking_list:
                    
                    booking_details = orm_to_dict(booking_list[0])
                    booking_details["booking_id"] = booking_details["id"]
                    booking_details["seat_ids"] = seat_ids

                    # fetching booking saga logs details
                    booking_saga_logs_list = await self.booking_repo.get_booking_saga_logs_details(
                        where_conditions = [
                            BookingSagaLogs.booking_id == booking_details["booking_id"],
                        ],
                        order_by = [
                            BookingSagaLogs.id.asc()
                        ]
                    )
                    if not booking_saga_logs_list:
                        return standardize_response(
                            status_code=404,
                            messages=[f"Booking saga log details not found for compensating"]
                        )                    
                    if booking_saga_logs_list:
                        for each_booking_sag_log in booking_saga_logs_list:
                            booking_details["booking_saga_log_id"] = each_booking_sag_log.id 
                            match each_booking_sag_log.saga_step:
                                case "HOLD_SEATS":
                                    rsp = await self.compensateHoldSeats(payload=booking_details)
                                case "CREATE_PAYMENT":
                                    rsp = await self.compensateCreatePayment(payload=booking_details)
                                case "CONFIRM_SEATS":
                                    pass                                    
                    

                    return standardize_response(
                        status_code=200,
                        messages=[f"Booking related all steps are compensated"]
                    )

        except Exception as e:
            return standardize_response(
                status_code=500,
                messages=[f"{str(e)}"]
            )



    async def compensateHoldSeats(self, *, payload: dict) -> dict:
        
        try:
            
            # extracted parameters
            user_id = int(payload.get("user_id", 0))
            schedule_id = int(payload.get("schedule_id", 0))
            seat_ids = payload.get("seat_ids", [])
            seat_ids.sort()
            from_station_sequence_number = int(payload.get("from_station_sequence_number", 0))
            to_station_sequence_number = int(payload.get("to_station_sequence_number", 0))
            booking_saga_log_id = int(payload.get("booking_saga_log_id", 0))

            if (
                user_id<=0 or schedule_id<=0 
                or not seat_ids 
                or from_station_sequence_number<=0 
                or to_station_sequence_number<=0
                or booking_saga_log_id<=0
            ):
                return standardize_response(
                    status_code=400,
                    messages=[f"Invalid parameters are passed for compensating on hold seats steps"]
                )

            # unlock hold seats into external inventory service
            unLockHoldSeatRspObj = None
            # unLockHoldSeatData = None
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{settings.INVENTORY_SERVICE_BASE_URL}/api/v1/inventory/schedules/seats/unlock", json={
                    "user_id" : user_id,
                    "schedule_id" : schedule_id,
                    "seat_ids" : seat_ids,
                    "from_station_sequence_number" : from_station_sequence_number,
                    "to_station_sequence_number" : to_station_sequence_number
                })
                unLockHoldSeatRspObj = response.json()
                # unLockHoldSeatData = unLockHoldSeatRspObj.get("data", None)
            print(f"unLockHoldSeatRspObj: {unLockHoldSeatRspObj}")
            
            # updating booking saga log table
            isBookingSagaLogsRecordUpdated = await self.booking_repo.update_booking_saga_logs_details(
                where_data={
                    "id": booking_saga_log_id
                },
                update_data = {
                    "status" : "COMPENSATED"
                }
            )

            await self._db_session.commit()

            return standardize_response(
                status_code=200,
                messages=[f"Compensated hold seats process successfully"]
            )

        except Exception as e:
            await self._db_session.rollback()
            return standardize_response(
                status_code=500,
                messages=[f"{str(e)}"]
            )
        


    async def compensateCreatePayment(self, *, payload: dict) -> dict:
        
        try:
            
            # extracted parameters
            idempotency_key = f"{payload.get("booking_id", 0)}-refund-compensation"
            payment_order_id = int(payload.get("payment_order_id", 0) or 0)
            amount = payload.get("total_amount", 0)
            reason = "booking_compensation"
            booking_saga_log_id = int(payload.get("booking_saga_log_id", 0))
            
            if (booking_saga_log_id<=0):
                return standardize_response(
                    status_code=400,
                    messages=[f"Invalid parameters are passed for compensating on create payment steps"]
                )
            
            # initiate refund process into external payment service
            refundPaymentRspObj = None
            # refundPaymentData = None
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{settings.PAYMENT_SERVICE_BASE_URL}/api/v1/payments/refunds", json={
                    "idempotency_key" : idempotency_key,
                    "payment_order_id" : payment_order_id,
                    "amount" : amount,
                    "reason" : reason,
                })
                refundPaymentRspObj = response.json()
                # refundPaymentData = refundPaymentRspObj.get("data", None)
            print(f"refundPaymentRspObj: {refundPaymentRspObj}")
            
            # updating booking saga log table
            isBookingSagaLogsRecordUpdated = await self.booking_repo.update_booking_saga_logs_details(
                where_data={
                    "id": booking_saga_log_id
                },
                update_data = {
                    "status" : "COMPENSATED"
                }
            )

            await self._db_session.commit()

            return standardize_response(
                status_code=200,
                messages=[f"Compensated created payment order process successfully"]
            )

        except Exception as e:
            await self._db_session.rollback()
            return standardize_response(
                status_code=500,
                messages=[f"{str(e)}"]
            )    



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
            allRedisSeatsLockKeys = []
            redisKeySeatsLockValue = ""
            
            # checking given idempotency key exists or not
            event_key = f"{idempotency_key}:booking"
            existing_idempotency_record = await self.idempotency_repo.get_idempotency_record_by_event_key(event_key)
            if existing_idempotency_record:
                return standardize_response(
                    status_code=400,
                    messages=[f"Booking already created. Duplicate request"],
                    data=existing_idempotency_record.event_response,
                )
            
            # fetching schedule availability from external inventory service
            inventoryScheduleDataObj = None
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{settings.INVENTORY_SERVICE_BASE_URL}/api/v1/inventory/schedules/{schedule_id}/availability")
                # response.raise_for_status()
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
                    status_code=400,
                    messages=[f"Inventory schedule not active for Train-Schedule-ID: {schedule_id}"],
                )
            departure_date = datetime.strptime(inventoryScheduleDataObj["departure_date"], "%Y-%m-%d").date()
            if departure_date<today_ist():
                return standardize_response(
                    status_code=400,
                    messages=[f"Train already departed for Train-Schedule-ID: {schedule_id}"],
                )
            
            # fetching seats details from external inventory service
            seatData = None
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{settings.INVENTORY_SERVICE_BASE_URL}/api/v1/inventory/schedules/{schedule_id}/seats", params={
                    "seat_ids" : ",".join(map(str, seat_ids)),
                    "from_station_sequence_number" : from_station_sequence_number,
                    "to_station_sequence_number" : to_station_sequence_number
                })
                # response.raise_for_status()
                data = response.json()
                seatData = data.get("data", None)
            print(f"seatData: {seatData}")
            if seatData == None:
                return standardize_response(
                    status_code=404,
                    messages=[f"Seat details not found for Train-Schedule-ID: {schedule_id}"],
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

        
            # preparing keys to acquire seat locks in redis via lua_script
            for eachSeatId in seat_ids:
                key = f"booking:lock:seat:{schedule_id}:{eachSeatId}:{from_station_sequence_number}:{to_station_sequence_number}"
                allRedisSeatsLockKeys.append(key)
            curTimeStamp = int(datetime.now().timestamp())    
            redisKeySeatsLockValue = f"pre-{curTimeStamp}:{curTimeStamp}"
            acquiredSeatLocksRedisResponse = await acquireBookingSeatLocksThroughRedis(allRedisSeatsLockKeys, redisKeySeatsLockValue, settings.BOOKING_TTL_SECONDS)
            print(f"acquiredSeatLocksRedisResponse: {acquiredSeatLocksRedisResponse}")
            if acquiredSeatLocksRedisResponse["isSuccess"] == False:
                return standardize_response(
                    status_code=400,
                    messages=[f"One or more seats are being booked by another user. Please try again"],
                )

            curDateTime = now_ist()
            locked_expires_at = (curDateTime + timedelta(seconds=settings.LOCK_TTL_SECONDS))

            # adding entries into bookings table
            created_booking = await self.booking_repo.create_booking(
                user_id=user_id,
                schedule_id=schedule_id,
                train_id=inventoryScheduleDataObj["train_id"],
                train_number=inventoryScheduleDataObj["train_number"],
                train_name=inventoryScheduleDataObj["train_name"],
                departure_date=datetime.strptime(inventoryScheduleDataObj["departure_date"], "%Y-%m-%d").date(),
                total_amount=totalAmount,
                seat_count=len(seat_ids),
                from_station_id=from_station_id,
                to_station_id=to_station_id,
                from_station_sequence_number=from_station_sequence_number,
                to_station_sequence_number=to_station_sequence_number,
                idempotency_key=idempotency_key,
                payment_order_id=None,
                locked_expires_at=locked_expires_at.strftime("%Y-%m-%d %H:%M:%S"),
                failure_reason=None,
                version=0,
                status="PENDING",
            )

            booking_details = orm_to_dict(created_booking)
            booking_details["booking_id"] = created_booking.id
            
            # adding entries into booking-seat table
            created_booking_seats = await self.booking_repo.create_booking_seats(
                booking_id=booking_details["booking_id"], 
                seat_details=bookingSeats
            )
            booking_details["seats"] = [orm_to_dict(seat) for seat in created_booking_seats]

            # adding entries into booking-passengers table
            created_booking_passengers = await self.booking_repo.create_booking_passengers(
                booking_id=booking_details["booking_id"], 
                passenger_details=passengers
            )
            booking_details["passengers"] = [orm_to_dict(passenger) for passenger in created_booking_passengers]

            # adding entries into booking-saga-logs table as hold_seats
            created_booking_saga_logs1 = await self.booking_repo.create_booking_saga_logs(
                booking_id = booking_details["booking_id"], 
                saga_step = "HOLD_SEATS", 
                request = {
                    "user_id" : booking_details["user_id"], 
                    "schedule_id" : booking_details["schedule_id"], 
                    "seat_ids" : seat_ids, 
                    "ttlSeconds" : settings.LOCK_TTL_SECONDS,
                    "from_station_sequence_number" : from_station_sequence_number, 
                    "to_station_sequence_number" : to_station_sequence_number                     
                },
                response = None, 
                error = None, 
                status = "PENDING"
            )
            booking_details["hold_seats_saga_logs"] = orm_to_dict(created_booking_saga_logs1)

            # commit the records into db level
            await self._db_session.commit()

            # hold seats into external inventory service
            holdSeatRspObj = None
            holdSeatData = None
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{settings.INVENTORY_SERVICE_BASE_URL}/api/v1/inventory/schedules/seats/lock", json={
                    "user_id" : booking_details["user_id"],
                    "schedule_id" : booking_details["schedule_id"],
                    "seat_ids" : seat_ids,
                    "ttl_seconds" : settings.LOCK_TTL_SECONDS,
                    "from_station_sequence_number" : from_station_sequence_number,
                    "to_station_sequence_number" : to_station_sequence_number
                })
                # response.raise_for_status()
                holdSeatRspObj = response.json()
                holdSeatData = holdSeatRspObj.get("data", None)
            print(f"holdSeatRspObj: {holdSeatRspObj}")
            if holdSeatRspObj == None:
                
                params1 = {
                    "booking_id" : booking_details["booking_id"],
                    "seat_ids" : seat_ids,
                    "reason" : f"Seats not locked into inventory external services."
                }
                compensatedRspObj = await self.compensateAll(payload=params1)

                # updating booking table as failed
                isBookingRecordUpdated = await self.booking_repo.update_booking_details(
                    where_data={
                        "id": booking_details["booking_id"]
                    },
                    update_data = {
                        "failure_reason" : params1["reason"][:90],
                        "status" : "FAILED",
                    }
                )
                await self._db_session.commit()

                releasedSeatLocksRedisResponse = await releaseBookingSeatLocksThroughRedis(allRedisSeatsLockKeys, redisKeySeatsLockValue)
                print(f"releasedSeatLocksRedisResponse: {releasedSeatLocksRedisResponse}")

                return standardize_response(
                    status_code=400,
                    messages=[f"Seats not locked into inventory external services."],
                )
            
            elif holdSeatRspObj.get("status_code") not in [200, 201]:

                params1 = {
                    "booking_id" : booking_details["booking_id"],
                    "seat_ids" : seat_ids,
                    "reason" : ", ".join(holdSeatRspObj.get("messages", ["Unknown error"]))
                }
                compensatedRspObj = await self.compensateAll(payload=params1)

                # updating booking table as failed
                isBookingRecordUpdated = await self.booking_repo.update_booking_details(
                    where_data={
                        "id": booking_details["booking_id"]
                    },
                    update_data = {
                        "failure_reason" : params1["reason"][:90],
                        "status" : "FAILED",
                    }
                )
                await self._db_session.commit()

                releasedSeatLocksRedisResponse = await releaseBookingSeatLocksThroughRedis(allRedisSeatsLockKeys, redisKeySeatsLockValue)
                print(f"releasedSeatLocksRedisResponse: {releasedSeatLocksRedisResponse}")

                return standardize_response(
                    status_code=holdSeatRspObj.get("status_code"),
                    messages=holdSeatRspObj.get("messages"),
                )
            

            # updating saga-logs table as compeleted
            isBookingSagaLogsRecordUpdated = await self.booking_repo.update_booking_saga_logs_details(
                where_data={
                    "id": created_booking_saga_logs1.id
                },
                update_data = {
                    "response" : holdSeatData,
                    "status" : "COMPLETED"
                }
            )
            booking_details["hold_seats_saga_logs"]["response"] = holdSeatData
            booking_details["hold_seats_saga_logs"]["status"] = "COMPLETED"

            # updating booking table as seats_held
            isBookingRecordUpdated = await self.booking_repo.update_booking_details(
                where_data={
                    "id": booking_details["booking_id"]
                },
                update_data = {
                    "status" : "SEATS_HELD"
                }
            )
            booking_details["status"] = "SEATS_HELD"

            # commit the records into db level
            await self._db_session.commit()
            
            # adding entries into booking-saga-logs table related to creating payment order request
            created_booking_saga_logs2 = await self.booking_repo.create_booking_saga_logs(
                booking_id = booking_details["booking_id"], 
                saga_step = "CREATE_PAYMENT", 
                request = {
                    "booking_id" : booking_details["booking_id"], 
                    "amount" : booking_details["total_amount"], 
                    "user_id" : booking_details["user_id"], 
                },
                response = None, 
                error = None, 
                status = "PENDING"
            )
            booking_details["create_payment_saga_logs"] = orm_to_dict(created_booking_saga_logs2)

            # commit the records into db level
            await self._db_session.commit()

            # creating payment order request into external payment services
            createdPaymentOrderRequestRspObj = None
            createdPaymentOrderRequestData = None
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{settings.PAYMENT_SERVICE_BASE_URL}/api/v1/payments/orders", json={
                    "idempotency_key" : f"{booking_details["booking_id"]}-payment",
                    "user_id" : booking_details["user_id"],
                    "booking_id" : booking_details["booking_id"],
                    "amount" : booking_details["total_amount"],
                })
                # response.raise_for_status()
                createdPaymentOrderRequestRspObj = response.json()
                createdPaymentOrderRequestData = createdPaymentOrderRequestRspObj.get("data", None)
            print(f"createdPaymentOrderRequestRspObj: {createdPaymentOrderRequestRspObj}")
            if createdPaymentOrderRequestRspObj == None:

                params1 = {
                    "booking_id" : booking_details["booking_id"],
                    "seat_ids" : seat_ids,
                    "reason" : "Payment orders not created into payment external services"
                }
                compensatedRspObj = await self.compensateAll(payload=params1)

                # updating booking table as failed
                isBookingRecordUpdated = await self.booking_repo.update_booking_details(
                    where_data={
                        "id": booking_details["booking_id"]
                    },
                    update_data = {
                        "failure_reason" : params1["reason"][:90],
                        "status" : "FAILED",
                    }
                )
                await self._db_session.commit()

                releasedSeatLocksRedisResponse = await releaseBookingSeatLocksThroughRedis(allRedisSeatsLockKeys, redisKeySeatsLockValue)
                print(f"releasedSeatLocksRedisResponse: {releasedSeatLocksRedisResponse}")

                return standardize_response(
                    status_code=404,
                    messages=[f"Payment orders not created into payment external services."],
                )
            
            elif createdPaymentOrderRequestRspObj.get("status_code") == 200:

                params1 = {
                    "booking_id" : booking_details["booking_id"],
                    "seat_ids" : seat_ids,
                    "reason" : "Payment orders already created into payment external services"
                }
                compensatedRspObj = await self.compensateAll(payload=params1)

                # updating booking table as failed
                isBookingRecordUpdated = await self.booking_repo.update_booking_details(
                    where_data={
                        "id": booking_details["booking_id"]
                    },
                    update_data = {
                        "failure_reason" : params1["reason"][:90],
                        "status" : "FAILED",
                    }
                )
                await self._db_session.commit()

                releasedSeatLocksRedisResponse = await releaseBookingSeatLocksThroughRedis(allRedisSeatsLockKeys, redisKeySeatsLockValue)
                print(f"releasedSeatLocksRedisResponse: {releasedSeatLocksRedisResponse}")

                return standardize_response(
                    status_code=400,
                    messages=[f"Payment orders already created into payment external services."],
                )
            
            elif createdPaymentOrderRequestRspObj.get("status_code") not in [200, 201]:

                params1 = {
                    "booking_id" : booking_details["booking_id"],
                    "seat_ids" : seat_ids,
                    "reason" : ", ".join(createdPaymentOrderRequestRspObj.get("messages", ["Unknown error"]))
                }
                compensatedRspObj = await self.compensateAll(payload=params1)

                # updating booking table as failed
                isBookingRecordUpdated = await self.booking_repo.update_booking_details(
                    where_data={
                        "id": booking_details["booking_id"]
                    },
                    update_data = {
                        "failure_reason" : params1["reason"][:90],
                        "status" : "FAILED",
                    }
                )
                await self._db_session.commit()

                releasedSeatLocksRedisResponse = await releaseBookingSeatLocksThroughRedis(allRedisSeatsLockKeys, redisKeySeatsLockValue)
                print(f"releasedSeatLocksRedisResponse: {releasedSeatLocksRedisResponse}")

                return standardize_response(
                    status_code=400,
                    messages=createdPaymentOrderRequestRspObj.get("messages")
                )

            booking_details["payment_orders"] = createdPaymentOrderRequestData
            booking_details["payment_order_id"] = createdPaymentOrderRequestData["payment_order_id"]

            # updating saga-logs table as completed
            isBookingSagaLogsRecordUpdated = await self.booking_repo.update_booking_saga_logs_details(
                where_data={
                    "id": created_booking_saga_logs2.id
                },
                update_data = {
                    "response" : createdPaymentOrderRequestData,
                    "status" : "COMPLETED"
                }
            )
            booking_details["create_payment_saga_logs"]["response"] = createdPaymentOrderRequestData
            booking_details["create_payment_saga_logs"]["status"] = "COMPLETED"

            # updating booking table as payment pending
            isBookingRecordUpdated = await self.booking_repo.update_booking_details(
                where_data={
                    "id": booking_details["booking_id"],
                },
                update_data = {
                    "payment_order_id" : createdPaymentOrderRequestData["payment_order_id"],
                    "status" : "PAYMENT_PENDING"
                }
            )
            booking_details["status"] = "PAYMENT_PENDING"

            
            # storing idempotency-key details
            await self.idempotency_repo.add_idempotency_record(
                event_key = event_key,
                event_type = "booking_created",
                event_response = booking_details
            )
            
            # commit the records into db level
            await self._db_session.commit()

            return standardize_response(
                status_code=201,
                messages=[f"Booking created"],
                data=booking_details
            )
            
        
        except Exception as e:
            
            params1 = {
                "booking_id" : booking_details.get("booking_id", 0),
                "seat_ids" : seat_ids,
                "reason" : str(e)
            }
            compensatedRspObj = await self.compensateAll(payload=params1)
            
            # updating booking table as failed
            isBookingRecordUpdated = await self.booking_repo.update_booking_details(
                where_data={
                    "id": booking_details.get("booking_id", 0),
                },
                update_data = {
                    "failure_reason" : str(e),
                    "status" : "FAILED"
                }
            )
            await self._db_session.commit()

            releasedSeatLocksRedisResponse = await releaseBookingSeatLocksThroughRedis(allRedisSeatsLockKeys, redisKeySeatsLockValue)
            print(f"releasedSeatLocksRedisResponse: {releasedSeatLocksRedisResponse}")

            return standardize_response(
                status_code=500,
                messages=[f"{str(e)}"]
            )
        


    async def verify_payment_details(self, *, payload: dict) -> dict:
        
        try:

            # extracted parameters
            user_id = payload.get("user_id", 0)
            booking_id = payload.get("booking_id", 0)
            gateway_payment_id = payload.get("gateway_payment_id", "")
            gateway_payment_signature = payload.get("gateway_payment_signature", "")

            # fetching booking details
            booking_list = await self.booking_repo.get_booking_details(
                where_conditions = [
                    Bookings.id == booking_id,
                ],
                order_by = [
                    Bookings.id.asc()
                ]
            )
            if not booking_list:
                return standardize_response(
                    status_code=404,
                    messages=[f"Booking details not found"]
                )
            if booking_list:

                if not booking_list[0].user_id == user_id:
                    return standardize_response(
                        status_code=404,
                        messages=[f"Booking details found not match with given user"]
                    )
                if booking_list[0].status == "CONFIRMED":
                    return standardize_response(
                        status_code=200,
                        messages=[f"Booking payment is already confirmed"]
                    )
                if booking_list[0].status != "PAYMENT_PENDING":
                    return standardize_response(
                        status_code=200,
                        messages=[f"Booking is in {booking_list[0].status} status, cannot verify payment"]
                    )
                
                # calling payment service to verify and capture
                verifyPaymentRspObj = None
                # verifyPaymentRspData = None
                async with httpx.AsyncClient() as client:
                    response = await client.post(f"{settings.PAYMENT_SERVICE_BASE_URL}/api/v1/payments/orders/verify", json={
                        "payment_order_id" : booking_list[0].payment_order_id,
                        "gateway_payment_id" : gateway_payment_id,
                        "gateway_payment_signature" : gateway_payment_signature,
                    })
                    verifyPaymentRspObj = response.json()
                    verifyPaymentRspData = verifyPaymentRspObj.get("data", None)
                print(f"verifyPaymentRspObj: {verifyPaymentRspObj}")
                if verifyPaymentRspObj == None:
                    return standardize_response(
                        status_code=400,
                        messages=[f"Payment orders not found"]
                    )
                
                return standardize_response(
                    status_code=verifyPaymentRspObj["status_code"],
                    messages=verifyPaymentRspObj["messages"],
                    data=verifyPaymentRspObj["data"],
                )
    
        except Exception as e:
            return standardize_response(
                status_code=500,
                messages=[f"{str(e)}"]
            )

    

    async def process_booking_payment_orders_success_details(self, *, payload: dict) -> dict:
        
        try:

            # extracted parameters
            booking_id = payload.get("booking_id", 0)
            payment_order_id = payload.get("payment_order_id", 0)
            gateway_order_id = payload.get("gateway_order_id", "")
            gateway_payment_id = payload.get("gateway_payment_id", "")
            amount = payload.get("amount", 0)
            reason = payload.get("reason", "")
            payment_order_status = payload.get("payment_order_status", "")

            if not all([
                booking_id > 0,
                payment_order_id > 0,
                gateway_order_id,
                gateway_payment_id,
                reason,
                payment_order_status == "CAPTURED"
            ]):
                return standardize_response(
                    status_code=400,
                    messages=[f"Invalid parameters are passsed for processing booking payment success details"]
                )
            
            # fetching booking details
            booking_list = await self.booking_repo.get_booking_details(
                where_conditions = [
                    Bookings.id == booking_id,
                    Bookings.payment_order_id == payment_order_id,
                ],
                order_by = [
                    Bookings.id.asc()
                ]
            )
            if not booking_list:
                return standardize_response(
                    status_code=404,
                    messages=[f"Booking not found for payment-order-id: {payment_order_id}"]
                )
            if booking_list:

                if booking_list[0].status == "CONFIRMED":
                    return standardize_response(
                        status_code=200,
                        messages=[f"Booking already confirmed for payment-order-id: {payment_order_id}"]
                    )
                if booking_list[0].status != "PAYMENT_PENDING":
                    return standardize_response(
                        status_code=400,
                        messages=[f"Booking {booking_id} in unexpected status {booking_list[0].status} for payment-order-id: {payment_order_id}"]
                    )
                # fetching booking seats details
                booking_seats_list = await self.booking_repo.get_booking_seats_details(
                    where_conditions = [
                        BookingSeats.booking_id == booking_id,
                    ]
                )
                if not booking_seats_list:
                    return standardize_response(
                        status_code=404,
                        messages=[f"Booking seats details not found for booking-id: {booking_id}, payment-order-id: {payment_order_id}"]
                    )
                # fetching booking passengers details
                booking_passengers_list = await self.booking_repo.get_booking_passengers_details(
                    where_conditions = [
                        BookingPassengers.booking_id == booking_id,
                    ]
                )
                if not booking_passengers_list:
                    return standardize_response(
                        status_code=404,
                        messages=[f"Booking passengers details not found for booking-id: {booking_id}, payment-order-id: {payment_order_id}"]
                    )  
                # fetching users details
                user_details = await self.user_repo.get_by_id(
                    user_id=booking_list[0].user_id
                )
                if not user_details:
                    return standardize_response(
                        status_code=404,
                        messages=[f"Booking user details not found for booking-id: {booking_id}, payment-order-id: {payment_order_id}"]
                    )  
                
                if True:

                    seat_ids = [eachBookingSeatObj.seat_id for eachBookingSeatObj in booking_seats_list]

                    # automically claim this booking — if expiry job or cancel already changed it, bail out
                    cnt_of_booking_records_updated = await self.booking_repo.update_booking_details(
                        where_data = {
                            "id" : booking_list[0].id,
                            "version" : booking_list[0].version,
                        },
                        update_data = {
                            "version" : booking_list[0].version + 1,
                            "status" : "CONFIRMING"
                        }
                    )
                    if cnt_of_booking_records_updated<=0:
                        return standardize_response(
                            status_code=200,
                            messages=[f"Booking {booking_id} already handled by another process, skipping"]
                        )
                    
                    # confirming seats into external inventory services
                    confirmedSeatRspObj = None
                    confirmedSeatData = None
                    async with httpx.AsyncClient() as client:
                        response = await client.post(f"{settings.INVENTORY_SERVICE_BASE_URL}/api/v1/inventory/schedules/seats/confirm", json={
                            "schedule_id" : booking_list[0].schedule_id,
                            "seat_ids" : seat_ids,
                            "booking_id" : booking_list[0].id,
                            "user_id" : booking_list[0].user_id,
                            "from_station_sequence_number" : booking_list[0].from_station_sequence_number,
                            "to_station_sequence_number" : booking_list[0].to_station_sequence_number,
                        })
                        confirmedSeatRspObj = response.json()
                        confirmedSeatData = confirmedSeatRspObj.get("data", None)
                    print(f"confirmedSeatRspObj: {confirmedSeatRspObj}")
                    
                    # updating booking status as confirmed
                    cnt_of_booking_records_updated = await self.booking_repo.update_booking_details(
                        where_data = {
                            "id" : booking_list[0].id,
                            "status" : "CONFIRMING",
                        },
                        update_data = {
                            "version" : booking_list[0].version + 1,
                            "status" : "CONFIRMED"
                        }
                    )

                    # releasing the seats locks from redis as forcing
                    allRedisSeatsLockKeys = []
                    for eachSeatId in seat_ids:
                        key = f"booking:lock:seat:{booking_list[0].schedule_id}:{eachSeatId}:{booking_list[0].from_station_sequence_number}:{booking_list[0].to_station_sequence_number}"
                        allRedisSeatsLockKeys.append(key)
                    releasedSeatLocksCntThroughRedis = await forceReleaseSeatLocksThroughRedis(allRedisSeatsLockKeys)
                    print(f"releasedSeatLocksCntThroughRedis: {releasedSeatLocksCntThroughRedis}")

                    # adding records into outbox events table
                    # data published into kafka-topics via workers and consumer will be consume the message
                    params1 = {
                        "booking_id" : booking_list[0].id,
                        "schedule_id" : booking_list[0].schedule_id,
                        "train_id" : booking_list[0].train_id,
                        "train_number" : booking_list[0].train_number,
                        "train_name" : booking_list[0].train_name,
                        "from_station_sequence_number" : booking_list[0].from_station_sequence_number,
                        "to_station_sequence_number" : booking_list[0].to_station_sequence_number,
                        "departure_date" : str(booking_list[0].departure_date),
                        "seats" : [
                            {
                                "seat_id" : seat.seat_id,
                                "seat_number" : seat.seat_number,
                                "seat_type" : seat.seat_type,
                                "seat_price" : str(seat.price)
                            }
                            for seat in booking_seats_list
                        ],
                        "passengers" : [
                            {
                                "id" : passenger.id,
                                "name" : passenger.name,
                                "age" : passenger.age,
                                "gender" : passenger.gender,
                            }
                            for passenger in booking_passengers_list
                        ],
                        "total_amount" : str(booking_list[0].total_amount),
                        "user_id" : booking_list[0].user_id,
                        "user_first_name" : user_details.first_name,
                        "user_email" : user_details.email,
                        "user_mobile" : user_details.mobile,
                        "booking_status_reason" : "Confirmation successfully",
                        "booking_status" : "CONFIRMED",
                    }
                    outbox_events_rsp = await self.store_booking_confirmed_into_outbox_events(payload=params1)
                    print(f"outbox_events_rsp: {outbox_events_rsp}")

                    await self._db_session.commit()

                    return standardize_response(
                        status_code=200,
                        messages=[f"Booking details processed successfully"],
                        data={
                            "booking_id" : booking_list[0].id,
                            "booking_status" : "CONFIRMED"
                        }
                    )


        except Exception as e:
            
            await self._db_session.rollback()

            # refund payment and release seats
            params1 = {
                "booking_id" : booking_list[0].id,
                "seat_ids" : seat_ids,
                "reason" : str(e)
            }
            compensatedRspObj = await self.compensateAll(payload=params1)

            # updating booking status as failed
            cnt_of_booking_records_updated = await self.booking_repo.update_booking_details(
                where_data = {
                    "id" : booking_list[0].id,
                    "status" : ["PAYMENT_PENDING", "CONFIRMING"],
                },
                update_data = {
                    "failure_reason" : f"confirmation failed: {str(e)[:60]}",
                    "version" : booking_list[0].version + 1,
                    "status" : "FAILED"
                }
            )
            
            # releasing the seats locks from redis as forcing
            allRedisSeatsLockKeys = []
            for eachSeatId in seat_ids:
                key = f"booking:lock:seat:{booking_list[0].schedule_id}:{eachSeatId}:{booking_list[0].from_station_sequence_number}:{booking_list[0].to_station_sequence_number}"
                allRedisSeatsLockKeys.append(key)
            releasedSeatLocksCntThroughRedis = await forceReleaseSeatLocksThroughRedis(allRedisSeatsLockKeys)
            print(f"releasedSeatLocksCntThroughRedis: {releasedSeatLocksCntThroughRedis}")
            
            # adding records into outbox events table
            # data published into kafka-topics via workers and consumer will be consume the message
            params1 = {
                "booking_id" : booking_list[0].id,
                "schedule_id" : booking_list[0].schedule_id,
                "train_id" : booking_list[0].train_id,
                "train_number" : booking_list[0].train_number,
                "train_name" : booking_list[0].train_name,
                "from_station_sequence_number" : booking_list[0].from_station_sequence_number,
                "to_station_sequence_number" : booking_list[0].to_station_sequence_number,
                "departure_date" : str(booking_list[0].departure_date),
                "seats" : [
                    {
                        "seat_id" : seat.seat_id,
                        "seat_number" : seat.seat_number,
                        "seat_type" : seat.seat_type,
                        "seat_price" : str(seat.price)
                    }
                    for seat in booking_seats_list
                ],
                "passengers" : [
                    {
                        "id" : passenger.id,
                        "name" : passenger.name,
                        "age" : passenger.age,
                        "gender" : passenger.gender,
                    }
                    for passenger in booking_passengers_list
                ],
                "total_amount" : str(booking_list[0].total_amount),
                "user_id" : booking_list[0].user_id,
                "user_first_name" : user_details.first_name,
                "user_email" : user_details.email,
                "user_mobile" : user_details.mobile,
                "booking_status_reason" : f"Confirmation failed: {str(e)[:60]}",
                "booking_status" : "FAILED",
            }
            outbox_events_rsp = await self.store_booking_confirmed_into_outbox_events(payload=params1)
            print(f"outbox_events_rsp: {outbox_events_rsp}")
            
            await self._db_session.commit()

            return standardize_response(
                status_code=500,
                messages=[f"{str(e)}"]
            )
        
    

    async def process_booking_payment_orders_failed_details(self, *, payload: dict) -> dict:
        
        try:

            # extracted parameters
            booking_id = payload.get("booking_id", 0)
            payment_order_id = payload.get("payment_order_id", 0)
            gateway_order_id = payload.get("gateway_order_id", "")
            gateway_payment_id = payload.get("gateway_payment_id", "")
            amount = payload.get("amount", 0)
            reason = payload.get("reason", "")
            payment_order_status = payload.get("payment_order_status", "")

            if not all([
                booking_id > 0,
                payment_order_id > 0,
                gateway_order_id,
                gateway_payment_id,
                reason,
                payment_order_status != "CAPTURED"
            ]):
                return standardize_response(
                    status_code=400,
                    messages=[f"Invalid parameters are passsed for processing booking payment failed details"]
                )
            
            # fetching booking details
            booking_list = await self.booking_repo.get_booking_details(
                where_conditions = [
                    Bookings.id == booking_id,
                    Bookings.payment_order_id == payment_order_id,
                ],
                order_by = [
                    Bookings.id.asc()
                ]
            )
            if not booking_list:
                return standardize_response(
                    status_code=404,
                    messages=[f"Booking not found for payment-order-id: {payment_order_id}"]
                )
            if booking_list:

                if booking_list[0].status in ["FAILED", "CANCELLED", "EXPIRED"]:
                    return standardize_response(
                        status_code=200,
                        messages=[f"Booking {booking_list[0].id} already in terminal state: {booking_list[0].status}"]
                    )
                if booking_list[0].status != "PAYMENT_PENDING":
                    return standardize_response(
                        status_code=400,
                        messages=[f"Booking {booking_id} in unexpected status {booking_list[0].status} for payment-order-id: {payment_order_id}"]
                    )
                # fetching booking seats details
                booking_seats_list = await self.booking_repo.get_booking_seats_details(
                    where_conditions = [
                        BookingSeats.booking_id == booking_id,
                    ]
                )
                if not booking_seats_list:
                    return standardize_response(
                        status_code=404,
                        messages=[f"Booking seats details not found for booking-id: {booking_id}, payment-order-id: {payment_order_id}"]
                    )
                # fetching booking passengers details
                booking_passengers_list = await self.booking_repo.get_booking_passengers_details(
                    where_conditions = [
                        BookingPassengers.booking_id == booking_id,
                    ]
                )
                if not booking_passengers_list:
                    return standardize_response(
                        status_code=404,
                        messages=[f"Booking passengers details not found for booking-id: {booking_id}, payment-order-id: {payment_order_id}"]
                    )  
                # fetching users details
                user_details = await self.user_repo.get_by_id(
                    user_id=booking_list[0].user_id
                )
                if not user_details:
                    return standardize_response(
                        status_code=404,
                        messages=[f"Booking user details not found for booking-id: {booking_id}, payment-order-id: {payment_order_id}"]
                    )  
                
                if True:

                    seat_ids = [eachBookingSeatObj.seat_id for eachBookingSeatObj in booking_seats_list]

                    # automically claim this booking — if expiry job or cancel already changed it, bail out
                    cnt_of_booking_records_updated = await self.booking_repo.update_booking_details(
                        where_data = {
                            "id" : booking_list[0].id,
                            "version" : booking_list[0].version,
                        },
                        update_data = {
                            "failure_reason" : reason,
                            "version" : booking_list[0].version + 1,
                            "status" : "FAILED"
                        }
                    )
                    if cnt_of_booking_records_updated<=0:
                        return standardize_response(
                            status_code=200,
                            messages=[f"Booking {booking_id} already handled by another process, skipping"]
                        )

                    # refund payment and release seats
                    params1 = {
                        "booking_id" : booking_list[0].id,
                        "seat_ids" : seat_ids,
                        "reason" : reason[:90],
                    }
                    compensatedRspObj = await self.compensateAll(payload=params1)

                    # releasing the seats locks from redis as forcing
                    allRedisSeatsLockKeys = []
                    for eachSeatId in seat_ids:
                        key = f"booking:lock:seat:{booking_list[0].schedule_id}:{eachSeatId}:{booking_list[0].from_station_sequence_number}:{booking_list[0].to_station_sequence_number}"
                        allRedisSeatsLockKeys.append(key)
                    releasedSeatLocksCntThroughRedis = await forceReleaseSeatLocksThroughRedis(allRedisSeatsLockKeys)
                    print(f"releasedSeatLocksCntThroughRedis: {releasedSeatLocksCntThroughRedis}")

                    # adding records into outbox events table
                    # data published into kafka-topics via workers and consumer will be consume the message
                    params1 = {
                        "booking_id" : booking_list[0].id,
                        "schedule_id" : booking_list[0].schedule_id,
                        "train_id" : booking_list[0].train_id,
                        "train_number" : booking_list[0].train_number,
                        "train_name" : booking_list[0].train_name,
                        "from_station_sequence_number" : booking_list[0].from_station_sequence_number,
                        "to_station_sequence_number" : booking_list[0].to_station_sequence_number,
                        "departure_date" : str(booking_list[0].departure_date),
                        "seats" : [
                            {
                                "seat_id" : seat.seat_id,
                                "seat_number" : seat.seat_number,
                                "seat_type" : seat.seat_type,
                                "seat_price" : str(seat.price)
                            }
                            for seat in booking_seats_list
                        ],
                        "passengers" : [
                            {
                                "id" : passenger.id,
                                "name" : passenger.name,
                                "age" : passenger.age,
                                "gender" : passenger.gender,
                            }
                            for passenger in booking_passengers_list
                        ],
                        "total_amount" : str(booking_list[0].total_amount),
                        "user_id" : booking_list[0].user_id,
                        "user_first_name" : user_details.first_name,
                        "user_email" : user_details.email,
                        "user_mobile" : user_details.mobile,
                        "booking_status_reason" : f"Payment failed: {reason[:60]}",
                        "booking_status" : "FAILED",
                    }
                    outbox_events_rsp = await self.store_booking_confirmed_into_outbox_events(payload=params1)
                    print(f"outbox_events_rsp: {outbox_events_rsp}")

                    await self._db_session.commit()

                    return standardize_response(
                        status_code=200,
                        messages=[f"Booking details processed successfully"],
                        data={
                            "booking_id" : booking_list[0].id,
                            "booking_status" : "FAILED"
                        }
                    )


        except Exception as e:
            return standardize_response(
                status_code=500,
                messages=[f"{str(e)}"]
            )
        


    async def get_booking_details_by_booking_id(self, *, payload: dict) -> dict:
        
        try:

            # extracted parameters
            booking_id = payload.get("booking_id", 0)
            user_id = payload.get("user_id", 0)
            
            if not all([
                booking_id > 0,
                user_id > 0,
            ]):
                return standardize_response(
                    status_code=400,
                    messages=[f"Invalid parameters are passsed for getting booking details"]
                )
            
            # fetching booking details
            booking_list = await self.booking_repo.get_booking_details(
                where_conditions = [
                    Bookings.id == booking_id,
                    Bookings.user_id == user_id,
                ],
                order_by = [
                    Bookings.id.asc()
                ]
            )
            if not booking_list:
                return standardize_response(
                    status_code=404,
                    messages=[f"Booking details not found"]
                )
            if booking_list:

                # fetching booking seats details
                booking_seats_list = await self.booking_repo.get_booking_seats_details(
                    where_conditions = [
                        BookingSeats.booking_id == booking_id,
                    ]
                )
                if not booking_seats_list:
                    return standardize_response(
                        status_code=404,
                        messages=[f"Booking seats details not found for booking-id: {booking_id}"]
                    )
                # fetching booking passengers details
                booking_passengers_list = await self.booking_repo.get_booking_passengers_details(
                    where_conditions = [
                        BookingPassengers.booking_id == booking_id,
                    ]
                )
                if not booking_passengers_list:
                    return standardize_response(
                        status_code=404,
                        messages=[f"Booking passengers details not found for booking-id: {booking_id}"]
                    )  
                # fetching users details
                user_details = await self.user_repo.get_by_id(
                    user_id=booking_list[0].user_id
                )
                if not user_details:
                    return standardize_response(
                        status_code=404,
                        messages=[f"Booking user details not found for booking-id: {booking_id}"]
                    )  
                
                if True:

                    response_data = {
                        "booking_id" : booking_list[0].id,
                        "schedule_id" : booking_list[0].schedule_id,
                        "train_id" : booking_list[0].train_id,
                        "train_number" : booking_list[0].train_number,
                        "train_name" : booking_list[0].train_name,
                        "from_station_sequence_number" : booking_list[0].from_station_sequence_number,
                        "to_station_sequence_number" : booking_list[0].to_station_sequence_number,
                        "departure_date" : str(booking_list[0].departure_date),
                        "seats" : [
                            {
                                "seat_id" : seat.seat_id,
                                "seat_number" : seat.seat_number,
                                "seat_type" : seat.seat_type,
                                "seat_price" : str(seat.price)
                            }
                            for seat in booking_seats_list
                        ],
                        "passengers" : [
                            {
                                "id" : passenger.id,
                                "name" : passenger.name,
                                "age" : passenger.age,
                                "gender" : passenger.gender,
                            }
                            for passenger in booking_passengers_list
                        ],
                        "total_amount" : str(booking_list[0].total_amount),
                        "created_at": str(booking_list[0].created_at),
                        "booking_status" : booking_list[0].status,
                    }
        
                    return standardize_response(
                        status_code=200,
                        messages=[f"Booking details found"],
                        data=response_data,
                    )


        except Exception as e:
            return standardize_response(
                status_code=500,
                messages=[f"{str(e)}"]
            )
        


    async def get_user_bookings(self, *, payload: dict) -> dict:
        
        try:

            # extracted parameters
            user_id = payload.get("user_id", 0)
            status = payload.get("status", "CONFIRMED")
            page = payload.get("page", 1)
            limit = payload.get("limit", 10)
            
            response_data_obj = await self.booking_repo.get_user_bookings(
                user_id = user_id,
                status = status,
                page = page,
                limit = limit,
            )
            if not response_data_obj["bookings"]:
                return standardize_response(
                    status_code=404,
                    messages=[f"User bookings not found"],
                    data=response_data_obj
                )
            
            return standardize_response(
                status_code=200,
                messages=[f"User bookings found"],
                data=response_data_obj
            )

        except Exception as e:
            return standardize_response(
                status_code=500,
                messages=[f"{str(e)}"]
            )
        

    async def cancel_booking_details(self, *, payload: dict) -> dict:
        
        try:

            # extracted parameters
            booking_id = payload.get("booking_id", 0)
            user_id = payload.get("user_id", 0)

            if not all([
                booking_id > 0,
                user_id > 0,
            ]):
                return standardize_response(
                    status_code=400,
                    messages=[f"Invalid parameters are passsed for cancelling booking details"]
                )
            
            # fetching booking details
            booking_list = await self.booking_repo.get_booking_details(
                where_conditions = [
                    Bookings.id == booking_id,
                    Bookings.user_id == user_id,
                ],
                order_by = [
                    Bookings.id.asc()
                ]
            )
            if not booking_list:
                return standardize_response(
                    status_code=404,
                    messages=[f"Booking not found"]
                )
            if booking_list:

                if booking_list[0].status in ["CANCELLED", "CANCELLING", "FAILED", "EXPIRED", "CONFIRMING"]:
                    return standardize_response(
                        status_code=200,
                        messages=[f"Booking {booking_list[0].id} already in terminal state: {booking_list[0].status}"]
                    )
                
                # fetching booking seats details
                booking_seats_list = await self.booking_repo.get_booking_seats_details(
                    where_conditions = [
                        BookingSeats.booking_id == booking_id,
                    ]
                )
                if not booking_seats_list:
                    return standardize_response(
                        status_code=404,
                        messages=[f"Booking seats details not found"]
                    )
                # fetching booking passengers details
                booking_passengers_list = await self.booking_repo.get_booking_passengers_details(
                    where_conditions = [
                        BookingPassengers.booking_id == booking_id,
                    ]
                )
                if not booking_passengers_list:
                    return standardize_response(
                        status_code=404,
                        messages=[f"Booking passengers details"]
                    )  
                
                # fetching users details
                user_details = await self.user_repo.get_by_id(
                    user_id=booking_list[0].user_id
                )
                if not user_details:
                    return standardize_response(
                        status_code=404,
                        messages=[f"Booking user details not found"]
                    )  
                
                if True:

                    seat_ids = [eachBookingSeatObj.seat_id for eachBookingSeatObj in booking_seats_list]

                    # automically claim this booking — if expiry job or cancel already changed it, bail out
                    cnt_of_booking_records_updated = await self.booking_repo.update_booking_details(
                        where_data = {
                            "id" : booking_list[0].id,
                            "version" : booking_list[0].version,
                        },
                        update_data = {
                            "failure_reason" : "User cancelled",
                            "version" : booking_list[0].version + 1,
                            "status" : "CANCELLING"
                        }
                    )
                    if cnt_of_booking_records_updated<=0:
                        return standardize_response(
                            status_code=409,
                            messages=[f"Booking {booking_id} already handled by another process, skipping"]
                        )

                    # cancel seats into external inventory services
                    cancelledSeatRspObj = None
                    cancelledSeatData = None
                    async with httpx.AsyncClient() as client:
                        response = await client.post(f"{settings.INVENTORY_SERVICE_BASE_URL}/api/v1/inventory/schedules/seats/cancel", json={
                            "schedule_id" : booking_list[0].schedule_id,
                            "booking_id" : booking_list[0].id,
                            "user_id" : booking_list[0].user_id,
                        })
                        cancelledSeatRspObj = response.json()
                        cancelledSeatData = cancelledSeatRspObj.get("data", None)
                    print(f"cancelledSeatRspObj: {cancelledSeatRspObj}")
                    

                    return standardize_response(
                        status_code=200,
                        messages=[f"Booking details processed successfully"],
                        data={
                            "booking_id" : booking_list[0].id,
                            "booking_status" : "FAILED"
                        }
                    )


        except Exception as e:
            return standardize_response(
                status_code=500,
                messages=[f"{str(e)}"]
            )



    async def store_booking_confirmed_into_outbox_events(
        self,
        payload: dict
    ):

        rsp = {
            "outbox_event_id" : 0
        }
        try:
            
            created_outbox_events_row = await self.outbox_repo.add_outbox_event(
                aggregate_type="BOOKINGS",
                aggregate_id=payload.get("booking_id", 0),
                event_type="BOOKINGS_UPDATED_STATUS",
                payload_json=payload,
                status="PENDING"
            )
            rsp = {
                "outbox_event_id" : created_outbox_events_row.id
            }
            
        except Exception as e:
            pass

        return rsp







       