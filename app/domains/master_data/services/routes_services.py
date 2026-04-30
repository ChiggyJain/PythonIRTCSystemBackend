
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from decimal import Decimal
from app.common.utils.datetime import now_ist
from app.core.exceptions import BaseAppException
from app.domains.master_data.repository.sqlalchemy_repo import MasterDataSQLAlchemyRepository
from app.infrastructure.outbox.repository.sqlalchemy_repo import OutboxEventsSQLAlchemyRepository


class RoutesService:

    OUTBOX_STATUS_PENDING = "PENDING"
    OUTBOX_EVENT_ROUTE_CREATED = "MASTERDATA_ROUTE_CREATED_V1"

    def __init__(self, db_session: AsyncSession):
        self._db_session = db_session
        self.masterdata_repo = MasterDataSQLAlchemyRepository(db_session)
        self.outbox_repo = OutboxEventsSQLAlchemyRepository(db_session)


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
        train_details = await self.masterdata_repo.get_train_by_id(train_id=train_id)
        if not train_details:
            raise BaseAppException(
                status_code=400,
                messages=[f"Train id {train_id} does not exist"],
            )

        # 2) station existence check
        station_ids = [item["station_id"] for item in station_details]
        existing_station_count = await self.masterdata_repo.count_existing_station_ids(station_ids=station_ids)
        if existing_station_count != len(station_ids):
            raise BaseAppException(
                status_code=400,
                messages=["One or more station_id does not exist"],
            )

        try:

            # create ROUTES row
            route = await self.masterdata_repo.create_route(
                train_id=train_id,
                status="A",
            )

            # create ROUTE_STATIONS rows
            route_stations = await self.masterdata_repo.create_route_stations(
                route_id=route.id,
                station_details=station_details,
                status="A",
            )

            # fetching train-seats details
            train_seats = await self.masterdata_repo.get_train_seats_by_train_id(
                train_id=train_id
            )

            # outbox event
            await self.outbox_repo.add_outbox_event(
                aggregate_type="ROUTES",
                aggregate_id=str(route.id),
                event_type=self.OUTBOX_EVENT_ROUTE_CREATED,
                payload_json={
                    "route_id": route.id,
                    "train_details" : {
                        "train_id": train_details.id,
                        "train_number": train_details.train_number,
                        "train_name": train_details.train_name,
                        "coach_name": train_details.coach_name,
                        "total_seats": train_details.total_seats,
                        "status": train_details.status,
                    },
                    "seat_details": [
                        {
                            "id": seat.id,
                            "seat_type": seat.seat_type,
                            "seat_number": seat.seat_number,
                            "price": float(seat.price) if isinstance(seat.price, Decimal) else seat.price,
                            "status": seat.status,
                        }
                        for seat in train_seats
                    ],
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
                    "route_status": route.status,
                    "event_type": self.OUTBOX_EVENT_ROUTE_CREATED,
                    "event_version": 1,
                    "created_by_admin_user_id": admin_user_id,
                    "correlation_id": correlation_id,
                    "request_id": request_id,
                    "event_created_at": str(now_ist()),
                },
                status=self.OUTBOX_STATUS_PENDING,
            )

            await self._db_session.commit()

        # handling rollback cases if any exception occurs
        except IntegrityError as ex:

            await self._db_session.rollback()
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
            await self._db_session.rollback()
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
