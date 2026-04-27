
from datetime import date
from sqlalchemy.exc import IntegrityError
from app.common.utils.datetime import now_ist
from app.core.exceptions import BaseAppException
from app.domains.master_data.repository.base import MasterDataRepositoryBase


class SchedulesService:

    OUTBOX_STATUS_PENDING = "PENDING"
    OUTBOX_EVENT_SCHEDULE_CREATED = "MASTERDATA_SCHEDULE_CREATED_V1"

    def __init__(self, repo: MasterDataRepositoryBase):
        self.repo = repo


    async def create_train_schedule(
        self,
        *,
        train_id: int,
        departure_date: date,
        admin_user_id: int,
        correlation_id: str | None = None,
        request_id: str | None = None,
    ) -> dict:
        
        """
        Flow:
        1) Validate train exists
        2) Validate route exists for train
        3) Load route_stations for route
        4) Validate route_stations integrity (sequence/time/distance)
        5) Insert schedule
        6) Insert outbox event
        7) Commit once
        """

        # 1) train must exist
        is_train_exists = await self.repo.train_exists(train_id=train_id)
        if not is_train_exists:
            raise BaseAppException(
                status_code=400,
                messages=[f"Train id {train_id} does not exist"],
            )

        # 2) route must exist for this train
        route = await self.repo.get_route_by_train_id(train_id=train_id)
        if not route:
            raise BaseAppException(
                status_code=400,
                messages=[f"Route does not exist for train id {train_id}"],
            )

        # 3) route stations must exist
        route_stations = await self.repo.get_route_stations_by_route_id(route_id=route.id)
        if not route_stations:
            raise BaseAppException(
                status_code=400,
                messages=[f"Route stations not found for train id {train_id}"],
            )

        # 4) validate route station integrity
        self._validate_route_stations(route_stations=route_stations)

        try:

            # 5) create schedule
            schedule = await self.repo.create_schedule(
                train_id=train_id,
                departure_date=departure_date,
                status="A",
            )

            # 6) create outbox event
            await self.repo.add_outbox_event(
                aggregate_type="SCHEDULE",
                aggregate_id=str(schedule.id),
                event_type=self.OUTBOX_EVENT_SCHEDULE_CREATED,
                payload_json={
                    "schedule_id": schedule.id,
                    "train_id": schedule.train_id,
                    "departure_date": str(schedule.departure_date),
                    "status": schedule.status,
                    "route_id": route.id,
                    "route_stations_snapshot": [
                        {
                            "id": rs.id,
                            "station_id": rs.station_id,
                            "sequence_number": rs.sequence_number,
                            "arrival_time": rs.arrival_time.strftime("%H:%M:%S"),
                            "departure_time": rs.departure_time.strftime("%H:%M:%S"),
                            "distance_from_origin": float(rs.distance_from_origin),
                            "status": rs.status,
                        }
                        for rs in route_stations
                    ],
                    "event_type": self.OUTBOX_EVENT_SCHEDULE_CREATED,
                    "event_version": 1,
                    "created_by_admin_user_id": admin_user_id,
                    "correlation_id": correlation_id,
                    "request_id": request_id,
                    "event_created_at": str(now_ist()),
                },
                status=self.OUTBOX_STATUS_PENDING,
            )

            # 7) single commit
            await self.repo.commit()

        # handling the rollback cases if any exception is occured
        except IntegrityError as ex:
            await self.repo.rollback()
            msg = str(getattr(ex, "orig", ex)).lower()
            # unique(train_id, departure_date)
            if "uq_trainid_depdate" in msg or (
                "schedules" in msg and "train_id" in msg and "departure_date" in msg
            ):
                raise BaseAppException(
                    status_code=400,
                    messages=["Schedule already exists for this train_id and departure_date"],
                )
            raise BaseAppException(
                status_code=400,
                messages=["Unable to create schedule due to data constraint violation"],
            )

        except Exception:
            await self.repo.rollback()
            raise

        return {
            "id": schedule.id,
            "train_id": schedule.train_id,
            "departure_date": str(schedule.departure_date),
            "status": schedule.status,
            "dispatch_status": "accepted",
        }


    def _validate_route_stations(self, *, route_stations: list) -> None:

        """
        Validates existing ROUTE_STATIONS data before creating schedule:
        - sequence must be 1..N
        - no time overlap: next arrival > previous departure
        - first distance must be 0
        - remaining distances must be >0
        """

        if not route_stations:
            raise BaseAppException(
                status_code=400,
                messages=["Route stations are required for schedule creation"],
            )

        # Already ordered by repository query, but keeping defensive sort
        ordered = sorted(route_stations, key=lambda x: x.sequence_number)

        seq_values = [row.sequence_number for row in ordered]
        expected = list(range(1, len(ordered) + 1))
        if seq_values != expected:
            raise BaseAppException(
                status_code=400,
                messages=[f"Route station sequence_number must be strict sequence 1..{len(ordered)}"],
            )

        # first station distance must be 0
        if float(ordered[0].distance_from_origin) != 0.0:
            raise BaseAppException(
                status_code=400,
                messages=["distance_from_origin must be 0 for first station (sequence_number=1)"],
            )

        # next stations distance must be >0
        for row in ordered[1:]:
            if float(row.distance_from_origin) <= 0:
                raise BaseAppException(
                    status_code=400,
                    messages=["distance_from_origin must be >0 for stations after sequence_number=1"],
                )

        # validate no overlap and each row arrival < departure
        for row in ordered:
            if row.arrival_time >= row.departure_time:
                raise BaseAppException(
                    status_code=400,
                    messages=["arrival_time must be less than departure_time for each station"],
                )

        for i in range(1, len(ordered)):
            prev_row = ordered[i - 1]
            curr_row = ordered[i]
            if curr_row.arrival_time <= prev_row.departure_time:
                raise BaseAppException(
                    status_code=400,
                    messages=["arrival_time and departure_time must not overlap between stations"],
                )
