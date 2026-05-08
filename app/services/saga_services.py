
import httpx
from app.infrastructure.database.session import AsyncSessionLocal
from app.domains.booking.repository.sqlalchemy_repo import BookingSQLAlchemyRepository


async def executeHoldSeats(booking, seat_ids, ttlSeconds, from_station_sequence_number, to_station_sequence_number):
    
    # storing booking saga logs
    # HOLD_SEATS and status=PENDING
    async with AsyncSessionLocal() as db:
        async with db.begin():
            booking_repo = BookingSQLAlchemyRepository(db)
            created_booking_saga_logs = await booking_repo.create_booking_saga_logs(
                booking_id = booking["id"], 
                saga_step = "HOLD_SEATS", 
                request = {
                    "user_id" : booking["user_id"], 
                    "schedule_id" : booking["schedule_id"], 
                    "seat_ids" : seat_ids, 
                    "ttlSeconds" : ttlSeconds,
                    "from_station_sequence_number" : from_station_sequence_number, 
                    "to_station_sequence_number" : to_station_sequence_number                     
                },
                response = None, 
                error = None, 
                status = "PENDING"
            )

    # managing hold seats and task is pending
    executedHoldSeatsData = None
    async with httpx.AsyncClient() as client:
        response = await client.post(f"http://127.0.0.1:8000/inventory/schedules/seats/lock", params={
            "schedule_id" : booking["schedule_id"],
            "seat_ids" : seat_ids,
            "user_id" : booking["user_id"],
            "ttlSeconds" : ttlSeconds,
            "from_station_sequence_number" : from_station_sequence_number, 
            "to_station_sequence_number" : to_station_sequence_number                      
        })
        response.raise_for_status()
        data = response.json()
        executedHoldSeatsData = data.get("data", None)

    # updating booking-saga-log and bookings record table
    isBookingSagaLogsRecordUpdated = False
    isBookingRecordUpdated = False
    async with AsyncSessionLocal() as db:
        async with db.begin():
            booking_repo = BookingSQLAlchemyRepository(db)
            isBookingSagaLogsRecordUpdated = await booking_repo.update_booking_saga_logs_details(
                where_data={
                    "id": created_booking_saga_logs.id
                },
                update_data = {
                    "response" : executedHoldSeatsData,
                    "status" : "COMPLETED"
                }
            )
            isBookingRecordUpdated = await booking_repo.update_booking_details(
                where_data={
                    "id": booking.id
                },
                update_data = {
                    "status" : "SEATS_HELD"
                }
            )
    
    return executedHoldSeatsData


async def executeCreatePayment(booking):
    
    idempotencyKey = f"{booking["id"]}-payment"

    # storing booking saga logs
    # CREATE_PAYMENT and status=PENDING
    async with AsyncSessionLocal() as db:
        async with db.begin():
            booking_repo = BookingSQLAlchemyRepository(db)
            created_booking_saga_logs = await booking_repo.create_booking_saga_logs(
                booking_id = booking["id"], 
                saga_step = "CREATE_PAYMENT", 
                request = {
                    "booking_id" : booking["id"],
                    "total_amount" : booking["total_amount"],
                    "user_id" : booking["user_id"]
                },
                response = None, 
                error = None, 
                status = "PENDING"
            )
    
    # creating payment order and task is pending
    createdPaymentOrderData = None
    async with httpx.AsyncClient() as client:
        response = await client.post(f"http://127.0.0.1:8000/payments/orders", params={
            "booking_id" : booking["id"],
            "total_amount" : booking["total_amount"],
            "user_id" : booking["user_id"],
            "idempotency_key" : idempotencyKey
        })
        response.raise_for_status()
        data = response.json()
        createdPaymentOrderData = data.get("data", None)

    # updating booking-saga-log and bookings record table
    isBookingSagaLogsRecordUpdated = False
    isBookingRecordUpdated = False
    async with AsyncSessionLocal() as db:
        async with db.begin():
            booking_repo = BookingSQLAlchemyRepository(db)
            isBookingSagaLogsRecordUpdated = await booking_repo.update_booking_saga_logs_details(
                where_data = {
                    "id" : created_booking_saga_logs.id
                },
                update_data = {
                    "response" : createdPaymentOrderData,
                    "status" : "COMPLETED"
                }
            )
            isBookingRecordUpdated = await booking_repo.update_booking_details(
                where_data = {
                    "id" : booking["id"]
                },
                update_data = {
                    "payment_order_id" : createdPaymentOrderData["payment_order_id"],
                    "status" : "PAYMENT_PENDING"
                }
            )
    
    return createdPaymentOrderData


async def compensateAll(booking, seat_ids):

    async with AsyncSessionLocal() as db:
        booking_repo = BookingSQLAlchemyRepository(db)
        booking_saga_logs = await booking_repo.get_booking_saga_logs_by_booking_id(booking_id=booking["id"], status="COMPLETED")
    
    for each_booking_sag_log in booking_saga_logs:
        match (each_booking_sag_log.saga_step):
            case "HOLD_SEATS":
                await compensateHoldSeats(booking, seat_ids)
            case "CREATE_PAYMENT":
                await compensateCreatePayment(booking)
            case "CONFIRM_SEATS":
                await compensateConfirmSeats(booking)
            


async def compensateHoldSeats(booking, seat_ids):
    
    # releaseSeats task is pending 

    # updating booking-saga-log and bookings record table
    isBookingSagaLogsRecordUpdated = False
    async with AsyncSessionLocal() as db:
        async with db.begin():
            booking_repo = BookingSQLAlchemyRepository(db)
            isBookingSagaLogsRecordUpdated = await booking_repo.update_booking_saga_logs_details(
                where_data={
                    "booking_id": booking["id"],
                    "saga_step" : "HOLD_SEATS",
                    "status" : "COMPLETED",
                },
                update_data = {
                    "status" : "COMPENSATED"
                }
            )

async def compensateConfirmSeats(booking):
    pass

async def compensateCreatePayment(booking):
    pass

        


        
    
                        