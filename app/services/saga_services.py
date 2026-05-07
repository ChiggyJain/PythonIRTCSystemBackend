
from app.infrastructure.database.session import AsyncSessionLocal
from app.domains.booking.repository.sqlalchemy_repo import BookingSQLAlchemyRepository

async def executeHoldSeats(booking, seat_ids, ttlSeconds, from_station_sequence_number, to_station_sequence_number):
    async with AsyncSessionLocal() as db:
        async with db.begin():
            booking_repo = BookingSQLAlchemyRepository(db)
            created_booking_saga_logs = await booking_repo.create_booking_saga_logs(
                booking_id=booking.id, 
                saga_step="HOLD_SEATS", 
                request={
                    "user_id" : booking.user_id, 
                    "schedule_id" : booking.schedule_id, 
                    "seat_ids" : seat_ids, 
                    "ttlSeconds" : ttlSeconds,
                    "from_station_sequence_number" : from_station_sequence_number, 
                    "to_station_sequence_number" : to_station_sequence_number                     
                },
                response=None, 
                error=None, 
                status="PENDING"
            )
    pass
                        