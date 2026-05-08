
from datetime import date, datetime, timedelta
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.utils.logger import app_logger
from app.core.exceptions import BaseAppException
from app.common.utils.datetime import now_ist, today_ist
from app.core.response import success_response, error_response
from app.common.repository.idempotency.sqlalchemy_repo import IdempotencySQLAlchemyRepository
from app.domains.inventory.repository.sqlalchemy_repo import InventorySQLAlchemyRepository


class InventoryService:

    

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.idempotency_repo = IdempotencySQLAlchemyRepository(db_session)
        self.inventory_repo = InventorySQLAlchemyRepository(db_session)


    async def process_schedule_created_event(self, *, payload: dict) -> dict:

        IDEMPOTENCY_EVENT_TYPE = "MASTERDATA_SCHEDULE_CREATED_V1"
        IDEMPOTENCY_EVENT_KEY_PREFIX = "SCHEDULES_CREATED"

        schedule_id = int(payload.get("schedule_id", 0))
        if schedule_id <= 0:
            raise BaseAppException(
                status_code=400,
                messages=["Invalid schedule_id in payload"],
            )

        event_key = f"{IDEMPOTENCY_EVENT_KEY_PREFIX}_{schedule_id}"
        existing = await self.idempotency_repo.get_idempotency_record_by_event_key(event_key)
        if existing:
            return {
                "status": "duplicate",
                "event_key": event_key,
                "schedule_id": schedule_id,
                "message": "Event already processed",
            }

        train_details = payload.get("train_details") or {}
        seat_details = payload.get("seat_details") or []
        station_details = payload.get("station_details") or []
        train_id = int(train_details.get("train_id", 0))
        train_number = str(train_details.get("train_number", ""))
        train_name = str(train_details.get("train_name", ""))
        departure_date_raw = str(payload.get("departure_date", ""))

        if train_id <= 0:
            raise BaseAppException(status_code=400, messages=["Invalid train_id in payload"])
        if not train_number:
            raise BaseAppException(status_code=400, messages=["Invalid train_number in payload"])
        if not train_name:
            raise BaseAppException(status_code=400, messages=["Invalid train_name in payload"])
        if not departure_date_raw:
            raise BaseAppException(status_code=400, messages=["Invalid departure_date in payload"])

        try:
            departure_date = date.fromisoformat(departure_date_raw)
        except ValueError:
            raise BaseAppException(
                status_code=400,
                messages=["departure_date must be in YYYY-MM-DD format"],
            )

        total_seats = len(seat_details)
        available_seats = total_seats
        locked = 0
        booked = 0

        try:

            schedule_inventory = await self.inventory_repo.add_schedule_inventory(
                schedule_id=schedule_id,
                train_id=train_id,
                train_number=train_number,
                train_name=train_name,
                departure_date=departure_date,
                total_seats=total_seats,
                available_seats=available_seats,
                locked=locked,
                booked=booked,
                status="ACTIVE",
            )

            if seat_details:
                await self.inventory_repo.add_seat_inventory_bulk(
                    schedule_inventory_id=schedule_inventory.id,
                    schedule_id=schedule_id,
                    seat_details=seat_details,
                )

            if station_details:
                await self.inventory_repo.add_route_stop_bulk(
                    schedule_id=schedule_id,
                    station_details=station_details,
                )

            await self.idempotency_repo.add_idempotency_record(
                event_key=event_key,
                event_type=IDEMPOTENCY_EVENT_TYPE,
            )

            await self.db.commit()

            return {
                "status": "processed",
                "event_key": event_key,
                "schedule_id": schedule_id,
            }

        except IntegrityError as exc:
            
            await self.db.rollback()
            msg = str(getattr(exc, "orig", exc)).lower()
            # duplicate event guard (race-safe)
            if "uq_eventKey" in msg or "eventKey" in msg:
                app_logger.info(f"Idempotent duplicate ignored | event_key={event_key}")
                return {
                    "status": "duplicate",
                    "event_key": event_key,
                    "schedule_id": schedule_id,
                    "message": "Event already processed",
                }
            raise BaseAppException(
                status_code=400,
                messages=["Unable to persist inventory due to data constraint violation"],
            )

        except BaseAppException:
            await self.db.rollback()
            raise

        except Exception:
            await self.db.rollback()
            raise



    async def get_inventory_schedules_availabiliity(self, schedule_id: int):
        inventory_schedules = await self.inventory_repo.get_inventory_schedules_by_schedule_id(schedule_id=schedule_id)
        if inventory_schedules == None:
            return error_response(
                messages = ["No inventory schedules found"],
                status_code = 400,
                data = None
            )
        else:
            return success_response(
                messages = ["Inventory schedules found"],
                status_code = 200,
                data = inventory_schedules
            )

    async def lockSeats(self, *, payload: dict):
        
        # extracted parameters
        user_id = int(payload.get("user_id", 0))
        schedule_id = int(payload.get("schedule_id", 0))
        seat_ids = payload.get("seat_ids", [])
        ttlSeconds = int(payload.get("ttlSeconds", 600))
        from_station_sequence_number = int(payload.get("from_station_sequence_number", 0))
        to_station_sequence_number = int(payload.get("to_station_sequence_number", 0))

        curDateTime = now_ist()
        dt = datetime.strptime(curDateTime, "%Y-%m-%d %H:%M:%S")
        locked_expires_at = dt + timedelta(seconds=ttlSeconds)

        # fetching schedule-inventory details
        inventory_schedules = await self.inventory_repo.get_inventory_schedules_by_schedule_id(schedule_id=schedule_id)        
        if inventory_schedules ==  None:
            raise BaseAppException(
                status_code=400,
                messages=[f"No inventory schedule found for Train-Schedule-ID: {schedule_id}"],
            )
        if inventory_schedules.status!="ACTIVE":
            raise BaseAppException(
                status_code=400,
                messages=[f"Inventory schedule is not active for Train-Schedule-ID: {schedule_id}"],
            )
        
        # making exclusively row-level seat locking details
        seat_inventory_list = await self.inventory_repo.lock_seats_for_booking(schedule_id=schedule_id, seat_ids=seat_ids)
        if len(seat_inventory_list)!=len(seat_ids):
            raise BaseAppException(
                status_code=400,
                messages=[f"Seat-Inventory is not found for Train-Schedule-ID: {schedule_id}"],
            )
        
        