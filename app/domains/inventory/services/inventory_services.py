
from decimal import Decimal
from datetime import date, datetime, timedelta
from typing import List
from sqlalchemy import select, update, or_, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.utils.logger import app_logger
from app.core.exceptions import BaseAppException
from app.common.utils.datetime import (
    now_ist, 
    today_ist
)
from app.common.utils.orm_to_dict import orm_to_dict
from app.core.response import (
    standardize_response, 
)
from app.core.settings import get_settings
from app.domains.inventory.models.seat_inventory_models import SeatInventory
from app.domains.inventory.models.schedule_inventory_models import ScheduleInventory
from app.domains.inventory.models.seat_segment_lock_models import SeatSegmentLockInventory
from app.common.repository.idempotency.sqlalchemy_repo import IdempotencySQLAlchemyRepository
from app.domains.inventory.repository.sqlalchemy_repo import InventorySQLAlchemyRepository


settings = get_settings()


class InventoryService:
    

    def __init__(self, db_session: AsyncSession):
        self._db_session = db_session
        self.idempotency_repo = IdempotencySQLAlchemyRepository(db_session)
        self.inventory_repo = InventorySQLAlchemyRepository(db_session)


    async def process_train_schedule_created_event_for_inventory(self, *, payload: dict) -> dict:

        try:
            
            IDEMPOTENCY_EVENT_TYPE = "MASTERDATA_SCHEDULE_CREATED"
            IDEMPOTENCY_EVENT_KEY_PREFIX = "SCHEDULES_CREATED"

            schedule_id = int(payload.get("schedule_id", 0))
            train_details = payload.get("train_details") or {}
            seat_details = payload.get("seat_details") or []
            station_details = payload.get("station_details") or []
            train_id = int(train_details.get("train_id", 0))
            train_number = str(train_details.get("train_number", ""))
            train_name = str(train_details.get("train_name", ""))
            departure_date_raw = str(payload.get("departure_date", ""))

            if schedule_id <= 0:
                return standardize_response(
                    status_code=400,
                    messages=["Invalid schedule_id in payload"],
                )
            if train_id <= 0:
                return standardize_response(status_code=400, messages=["Invalid train_id in payload"])
            if not train_number:
                return standardize_response(status_code=400, messages=["Invalid train_number in payload"])
            if not train_name:
                return standardize_response(status_code=400, messages=["Invalid train_name in payload"])
            if not departure_date_raw:
                return standardize_response(status_code=400, messages=["Invalid departure_date in payload"])
            
            # checking idempotency key
            event_key = f"{IDEMPOTENCY_EVENT_KEY_PREFIX}:{schedule_id}"
            existing = await self.idempotency_repo.get_idempotency_record_by_event_key(event_key)
            if existing:
                return standardize_response(
                    status_code=201,
                    messages=["Schedule already processed"],
                    data={
                        "schedule_id": schedule_id,
                    }
                )

            try:
                departure_date = date.fromisoformat(departure_date_raw)
            except ValueError as e:
                return standardize_response(
                    status_code=400,
                    messages=["departure_date must be in YYYY-MM-DD format"],
                )

            total_seats = len(seat_details)
            available_seats = total_seats
            locked = 0
            booked = 0
            
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

            await self._db_session.commit()

            return standardize_response(
                status_code=201,
                messages=["Schedule processed"],
                data={
                    "schedule_id": schedule_id,
                }
            )
        
        except IntegrityError as ex:
            await self._db_session.rollback()
            msg = str(getattr(ex, "orig", ex)).lower()
            return standardize_response(
                status_code=400,
                messages=[f"Unable to create train route due to data constraint violation. {msg}"],
            )
        
        except BaseAppException as e:
            await self._db_session.rollback()
            raise e
        
        except Exception as e:
            await self._db_session.rollback()
            return standardize_response(
                status_code=500,
                messages=[f"{str(e)}"]
            )


    async def get_inventory_schedule_availabiliity(self, schedule_id: int):
        inventory_schedule = await self.inventory_repo.get_inventory_schedule_by_schedule_id(schedule_id=schedule_id)
        if not inventory_schedule:
            return standardize_response(
                status_code=404,
                messages=[f"No schedule inventory found"],
            )
        else:
            return standardize_response(
                status_code=200,
                messages=["Schedule inventory found"],
                data={
                    "schedule_inventory_id" : inventory_schedule.id,
                    "schedule_id" : inventory_schedule.schedule_id,
                    "train_id" : inventory_schedule.train_id,
                    "train_number" : inventory_schedule.train_number,
                    "train_name" : inventory_schedule.train_name,
                    "departure_date" : str(inventory_schedule.departure_date),
                    "total_seats" : inventory_schedule.total_seats,
                    "available_seats" : inventory_schedule.available_seats,
                    "locked" : inventory_schedule.locked,
                    "booked" : inventory_schedule.booked,
                    "status" : inventory_schedule.status,
                }
            )
        

    async def get_inventory_schedule_seats_availabiliity(
        self, 
        schedule_id: int = 0, 
        seat_ids: List[int] = [],
        from_station_sequence_number: int = 0, 
        to_station_sequence_number: int = 0
    ):

        try:
            
            inventory_schedule = await self.inventory_repo.get_inventory_schedule_by_schedule_id(schedule_id=schedule_id)
            if not inventory_schedule:
                return standardize_response(
                    status_code=404,
                    messages=[f"No schedule inventory found"],
                )
            else:

                seat_inventory_list = await self.inventory_repo.get_seat_inventory_details(
                    where_conditions = [
                        SeatInventory.schedule_id == schedule_id,
                        SeatInventory.seat_id.in_(seat_ids)
                    ],
                    order_by = [
                        SeatInventory.seat_number.asc()
                    ]
                )

                seat_segement_overlapping_lock_list = await self.inventory_repo.get_seat_segement_lock_details(
                    select_columns = [
                        SeatSegmentLockInventory.seat_id, 
                        SeatSegmentLockInventory.status
                    ],
                    where_conditions = [
                        SeatSegmentLockInventory.schedule_id == schedule_id,
                        SeatSegmentLockInventory.seat_id.in_(seat_ids),
                        SeatSegmentLockInventory.status.in_(["LOCKED", "BOOKED"]),
                        SeatSegmentLockInventory.from_station_sequence_number < to_station_sequence_number,
                        SeatSegmentLockInventory.to_station_sequence_number > from_station_sequence_number,
                    ],
                    order_by = [
                        SeatSegmentLockInventory.seat_id.asc()
                    ]
                )

                blocked_seat_ids = set(lock.seat_id for lock in seat_segement_overlapping_lock_list)

                seat_segement_withany_lock_list = await self.inventory_repo.get_seat_segement_lock_details(
                    select_columns = [
                        SeatSegmentLockInventory.seat_id,
                    ],
                    where_conditions = [
                        SeatSegmentLockInventory.schedule_id == schedule_id,
                        SeatSegmentLockInventory.seat_id.in_(seat_ids),
                        SeatSegmentLockInventory.status.in_(["LOCKED", "BOOKED"]),
                    ],
                    order_by = [
                        SeatSegmentLockInventory.seat_id.asc()
                    ]
                )

                seats_with_locks = set(lock.seat_id for lock in seat_segement_withany_lock_list)
                updated_seats = []

                for seat in seat_inventory_list:
                    seat_data = orm_to_dict(seat)
                    if seat_data["seat_id"] in blocked_seat_ids:
                        seat_data["segment_status"] = "UNAVAILABLE"
                    elif (
                        seat_data["status"] in ["BOOKED", "LOCKED"]
                        and seat_data["seat_id"] not in seats_with_locks
                    ):
                        seat_data["segment_status"] = "UNAVAILABLE"
                    else:
                        seat_data["segment_status"] = "AVAILABLE"
                    updated_seats.append({
                        "schedule_id" : seat_data["schedule_id"],
                        "seat_id" : seat_data["seat_id"],
                        "seat_number" : seat_data["seat_number"],
                        "seat_type" : seat_data["seat_type"],
                        "price" : float(seat_data["price"]) if isinstance(seat_data["price"], Decimal) else seat_data["price"],
                        "segment_status" : seat_data["segment_status"],
                        "status" : seat_data["status"],
                    })

                if len(updated_seats)<0:
                    return standardize_response(
                        status_code=404,
                        messages=["Seats details not found"],
                    )
                else:
                    return standardize_response(
                        status_code=200,
                        messages=["Seats details found"],
                        data={
                            "schedule_id" : schedule_id,
                            "total_seats" : inventory_schedule.total_seats,
                            "seats" : updated_seats
                        }
                    )
                
        except Exception as e:
            return standardize_response(
                status_code=500,
                messages=[f"{str(e)}"]
            )


    async def lock_seats(self, *, payload: dict):
        
        try:
            
            # extracted parameters
            user_id = int(payload.get("user_id", 0))
            schedule_id = int(payload.get("schedule_id", 0))
            seat_ids = payload.get("seat_ids", [])
            ttl_seconds = int(payload.get("ttl_seconds", 600))
            from_station_sequence_number = int(payload.get("from_station_sequence_number", 0))
            to_station_sequence_number = int(payload.get("to_station_sequence_number", 0))
            curDateTime = now_ist()
            locked_expires_at = (curDateTime + timedelta(seconds=ttl_seconds))

            if not seat_ids:
                return standardize_response(
                    status_code=400,
                    messages=["seat_ids is required"],
                )
            
            # fetching schedule-inventory details
            inventory_schedule = await self.inventory_repo.get_inventory_schedule_by_schedule_id(schedule_id=schedule_id)        
            if not inventory_schedule:
                return standardize_response(
                    status_code=404,
                    messages=[f"Schedule inventory not found"],
                )
            if inventory_schedule.status!="ACTIVE":
                return standardize_response(
                    status_code=400,
                    messages=[f"Schedule inventory is not active"],
                )

            # row-level lock on requested seats
            locked_seat_inventory_list = await self.inventory_repo.lock_seats_inventory_for_booking(
                schedule_id=schedule_id, seat_ids=seat_ids
            )

            # all requested seats must exist
            if len(locked_seat_inventory_list)!=len(seat_ids):
                found_ids = {
                    row.seat_id
                    for row in locked_seat_inventory_list
                }
                missing_ids = [
                    seat_id
                    for seat_id in seat_ids
                    if seat_id not in found_ids
                ]
                return standardize_response(
                    status_code=409,
                    messages=[f"Seats already locked: {missing_ids}"],
                )

            # check for overlapping segment locks on any of the requested seats
            overlapping_lock_seat_segment_list = await self.inventory_repo.lock_seat_segment_for_booking(
                schedule_id=schedule_id, 
                seat_ids=seat_ids, 
                from_station_sequence_number=from_station_sequence_number, 
                to_station_sequence_number=to_station_sequence_number
            )
            if overlapping_lock_seat_segment_list:
                blocked_seat_ids = list({
                    row.seat_id
                    for row in overlapping_lock_seat_segment_list
                })
                return standardize_response(
                    status_code=409,
                    messages=[
                        f"Seats already booked/locked: {blocked_seat_ids}"    
                    ],
                )
            
            # create segment seat lock rows for the requested segment
            # bulk adding
            seat_segment_lock_payloads = []
            for seat in locked_seat_inventory_list:
                seat_segment_lock_payloads.append({
                    "schedule_id": schedule_id,
                    "seat_id": seat.seat_id,
                    "from_station_sequence_number": from_station_sequence_number,
                    "to_station_sequence_number": to_station_sequence_number,
                    "locked_at" : now_ist(),
                    "locked_by_user_id": user_id,
                    "locked_expires_at": locked_expires_at,
                    "status" : "LOCKED"
                })
            await self.inventory_repo.add_seat_segement_lock_details(
                schedule_id=schedule_id,
                seat_details=seat_segment_lock_payloads
            )

            # set lockedBy/lockedAt/lockExpiresAt on seat-inventory that didn't have it yet
            seat_pk_ids = [row.id for row in locked_seat_inventory_list]
            await self.inventory_repo.update_seat_inventory_details(
                where_data={
                    "id": seat_pk_ids
                },
                update_data={
                    "locked_by_user_id": user_id,
                    "locked_at": now_ist(),
                    "locked_expires_at": locked_expires_at
                }
            )

            # recompute each seat's summary status from its segment locks
            recomputed_segment_seat_status_rsp_obj = await self.recompute_segment_seat_statuses(
                schedule_id=schedule_id,
                seat_ids=seat_ids
            )            

            # recount aggregates from actual seat rows (prevents counter drift)
            recounts_schedule_aggregates_status_rsp_obj = await self.recount_schedule_aggregates(
                schedule_id=schedule_id
            )

            await self._db_session.commit()

            """
            # task is pending
            # publish seats-availability update (fire and forget) into kafka topics
            # elastic search route_indexes based on schedule_id and train_id
            # schedule_id, train_id, count.available, counts.locked, counts.booked
            """

            return standardize_response(
                status_code=200,
                messages=["Seats locked successfully"],
                data={
                    "schedule_id": schedule_id,
                    "train_id" : inventory_schedule.train_id,
                    "locked_seats": [
                        {
                            "seat_id": seat.seat_id,
                            "seat_number": seat.seat_number,
                            "lock_expires_at": locked_expires_at.strftime(
                                "%Y-%m-%d %H:%M:%S"
                            )
                        }
                        for seat in locked_seat_inventory_list
                    ],
                    "lock_expires_at": locked_expires_at.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "counts": recounts_schedule_aggregates_status_rsp_obj
                }
            )


        except BaseAppException as e:
            await self._db_session.rollback()
            return standardize_response(
                status_code=500,
                messages=[str(e)],
            )

        except Exception as e:
            await self._db_session.rollback()
            return standardize_response(
                status_code=500,
                messages=[str(e)],
            )




    async def recompute_segment_seat_statuses(
        self,
        schedule_id: int,
        seat_ids: list[str]
    ):


        status_changes = {
            "status_code" : 500,
            "messages" : [f"Operation failed"],
            "now_available": 0,
            "now_occupied": 0,
            "locked_to_booked": 0,
            "booked_to_locked": 0,
        }
        
        try:
                
            for seat_id in seat_ids:

                # fetch seat segment locks
                lock_stmt = (
                    select(
                        SeatSegmentLockInventory.status
                    )
                    .where(
                        SeatSegmentLockInventory.schedule_id == schedule_id,
                        SeatSegmentLockInventory.seat_id == seat_id,
                        SeatSegmentLockInventory.status.in_(["LOCKED", "BOOKED"])
                    )
                )
                lock_result = await self._db_session.execute(lock_stmt)
                locks = lock_result.scalars().all()

                # Determine final seat status
                if len(locks) == 0:
                    new_status = "AVAILABLE"
                elif "LOCKED" in locks:
                    new_status = "LOCKED"
                else:
                    new_status = "BOOKED"

                # fetch seat inventory row
                seat_stmt = (
                    select(SeatInventory)
                    .where(
                        SeatInventory.schedule_id == schedule_id,
                        SeatInventory.seat_id == seat_id
                    )
                    .with_for_update(skip_locked=True)
                )
                seat_result = await self._db_session.execute(seat_stmt)
                seat_inventory = seat_result.scalar_one_or_none()
                if seat_inventory is None:
                    continue

                old_status = seat_inventory.status

                # Skip if no changes
                if old_status == new_status:
                    continue

                # Transition tracking
                if (
                    old_status == "AVAILABLE"
                    and new_status != "AVAILABLE"
                ):
                    status_changes["now_occupied"] += 1

                if (
                    old_status != "AVAILABLE"
                    and new_status == "AVAILABLE"
                ):
                    status_changes["now_available"] += 1

                if (
                    old_status == "LOCKED"
                    and new_status == "BOOKED"
                ):
                    status_changes["locked_to_booked"] += 1

                if (
                    old_status == "BOOKED"
                    and new_status == "LOCKED"
                ):
                    status_changes["booked_to_locked"] += 1

                # Update inventory seat status
                seat_inventory.status = new_status

                # Reset lock/booking metadata
                if new_status == "AVAILABLE":
                    seat_inventory.locked_by_user_id = None
                    seat_inventory.locked_at = None
                    seat_inventory.locked_expires_at = None
                    seat_inventory.booking_id = None

                seat_inventory.version+= 1

            status_changes["status_code"] = 200
            status_changes["messages"] = f"Operation success"

        except Exception as e:
            status_changes = {
                "status_code" : 500,
                "messages" : [f"{str(e)}"],
                "now_available": 0,
                "now_occupied": 0,
                "locked_to_booked": 0,
                "booked_to_locked": 0,
            }
        
        return status_changes



    async def recount_schedule_aggregates(
        self,
        schedule_id: int
    ):

        count_changes = {
            "status_code" : 500,
            "messages" : [f"Operation failed"],
            "available": 0,
            "locked": 0,
            "booked": 0,
        }

        try:
            
            # fetching seats summary from seat-inventory
            stmt = (
                select(
                    func.count().filter(
                        SeatInventory.status == "AVAILABLE"
                    ).label("available"),
                    func.count().filter(
                        SeatInventory.status == "LOCKED"
                    ).label("locked"),
                    func.count().filter(
                        SeatInventory.status == "BOOKED"
                    ).label("booked"),
                )
                .where(
                    SeatInventory.schedule_id == schedule_id
                )
            )
            result = await self._db_session.execute(stmt)
            counts = result.mappings().one()

            # fetching schedule inventory details for updating seats summary counters
            schedule_stmt = (
                select(ScheduleInventory)
                .where(
                    ScheduleInventory.schedule_id == schedule_id
                )
                .with_for_update(skip_locked=True)
            )
            schedule_result = await self._db_session.execute(
                schedule_stmt
            )
            schedule_inventory = (
                schedule_result.scalar_one_or_none()
            )

            if schedule_inventory:
                schedule_inventory.available = counts["available"]
                schedule_inventory.locked = counts["locked"]
                schedule_inventory.booked = counts["booked"]
                schedule_inventory.version += 1

            count_changes = {
                "status_code" : 200,
                "messages" : [f"Operation success"],
                "available": counts["available"],
                "locked": counts["locked"],
                "booked": counts["booked"],
            }
        
        except Exception as e:
            count_changes = {
                "status_code" : 500,
                "messages" : [f"{str(e)}"],
                "available": 0,
                "locked": 0,
                "booked": 0,
            }

        return count_changes

        



    

         




        
        

        