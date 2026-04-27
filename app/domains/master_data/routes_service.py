
from sqlalchemy.exc import IntegrityError
from app.common.utils.datetime import now_ist
from app.core.exceptions import BaseAppException
from app.domains.master_data.repository.base import MasterDataRepositoryBase


class RoutesService:

    OUTBOX_STATUS_PENDING = "PENDING"
    OUTBOX_EVENT_ROUTE_CREATED = "MASTERDATA_ROUTE_CREATED_V1"

    def __init__(self, repo: MasterDataRepositoryBase):
        self.repo = repo


    async def create_train_route(
        self,
        *,
        train_id: int,
        station_details: list[dict],
        admin_user_id: int,
        correlation_id: str | None = None,
        request_id: str | None = None,
    ) -> dict:
        
        """
        Flow:
        1) Check train exists
        2) Check all station_ids exist
        3) Insert ROUTES
        4) Insert ROUTE_STATIONS
        5) Insert OUTBOX_EVENTS
        6) Commit once
        """

        # 1) train existence check
        is_train_exists = await self.repo.train_exists(train_id=train_id)
        if not is_train_exists:
            raise BaseAppException(
                status_code=400,
                messages=[f"Train id {train_id} does not exist"],
            )

        # 2) station existence check
        station_ids = [item["station_id"] for item in station_details]
        existing_station_count = await self.repo.count_existing_station_ids(station_ids=station_ids)
        if existing_station_count != len(station_ids):
            raise BaseAppException(
                status_code=400,
                messages=["One or more station_id does not exist"],
            )

        try:

            # 3) create ROUTES row
            route = await self.repo.create_route(
                train_id=train_id,
                status="A",
            )

            # 4) create ROUTE_STATIONS rows
            route_stations = await self.repo.create_route_stations(
                route_id=route.id,
                station_details=station_details,
                status="A",
            )

            # 5) outbox event
            await self.repo.add_outbox_event(
                aggregate_type="ROUTE",
                aggregate_id=str(route.id),
                event_type=self.OUTBOX_EVENT_ROUTE_CREATED,
                payload_json={
                    "route_id": route.id,
                    "train_id": route.train_id,
                    "status": route.status,
                    "station_details": [
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
                    "event_type": self.OUTBOX_EVENT_ROUTE_CREATED,
                    "event_version": 1,
                    "created_by_admin_user_id": admin_user_id,
                    "correlation_id": correlation_id,
                    "request_id": request_id,
                    "event_created_at": str(now_ist()),
                },
                status=self.OUTBOX_STATUS_PENDING,
            )

            # 6) single commit
            await self.repo.commit()

        # handling rollback cases if any exception occurs
        except IntegrityError as ex:

            await self.repo.rollback()
            msg = str(getattr(ex, "orig", ex)).lower()

            # ROUTES unique(train_id)
            if "uq_trainid" in msg or ("routes" in msg and "train_id" in msg):
                raise BaseAppException(
                    status_code=400,
                    messages=["Route already exists for this train_id"],
                )

            # ROUTE_STATIONS unique(route_id, sequence_number) / unique(route_id, station_id)
            if "uq_routeid_seqnumber" in msg or "uq_routeid_stationid" in msg:
                raise BaseAppException(
                    status_code=400,
                    messages=["Duplicate sequence_number or station_id in route details"],
                )

            raise BaseAppException(
                status_code=400,
                messages=["Unable to create train route due to data constraint violation"],
            )

        except Exception:
            await self.repo.rollback()
            raise


        return {
            "id": route.id,
            "train_id": route.train_id,
            "status": route.status,
            "station_details": [
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
            "dispatch_status": "accepted",
        }
