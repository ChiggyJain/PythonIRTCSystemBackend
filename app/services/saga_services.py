
import httpx
from app.infrastructure.database.session import AsyncSessionLocal
from app.domains.booking.repository.sqlalchemy_repo import BookingSQLAlchemyRepository

async def executeHoldSeats(booking, seat_ids, ttlSeconds, from_station_sequence_number, to_station_sequence_number):
    
    # storing booking saga logs
    # step1: HOLD_SEATS and status=PENDING
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

    # storing hold seats
    executedHoldSeatsData = None
    async with httpx.AsyncClient() as client:
        response = await client.post(f"http://127.0.0.1:8000/inventory/seats/lock", params={
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

    # updating booking-saga-log table
    
    


        
    
                        