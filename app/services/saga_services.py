
import httpx
from app.infrastructure.database.session import AsyncSessionLocal
from app.domains.booking.repository.sqlalchemy_repo import BookingSQLAlchemyRepository


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

        


        
    
                        