
from datetime import date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.common.utils.datetime import now_ist
from app.core.exceptions import BaseAppException
from app.core.response import (
    standardize_response, 
    standardize_response,
    standardize_response
)
from app.core.settings import get_settings
from app.common.utils.ratelimiter import rate_limiter

from app.domains.master_data.repository.sqlalchemy_repo import MasterDataSQLAlchemyRepository
from app.infrastructure.outbox.repository.sqlalchemy_repo import OutboxEventsSQLAlchemyRepository


settings = get_settings()


class TrainSchedulesService:

    OUTBOX_STATUS_PENDING = "PENDING"
    OUTBOX_EVENT_SCHEDULE_CREATED = "MASTERDATA_SCHEDULE_CREATED"

    def __init__(self, db_session: AsyncSession):
        self._db_session = db_session
        self.masterdata_repo = MasterDataSQLAlchemyRepository(db_session)
        self.outbox_repo = OutboxEventsSQLAlchemyRepository(db_session)


    async def create_train_schedule(
        self,
        *,
        payload:dict,
    ) -> dict:
        
        try:

            # extracted parameters
            train_id = int(payload.get("train_id", 0))
            departure_date = payload.get("departure_date", "")
            user_id = payload.get("user_id", 0)
            correlation_id = payload.get("correlation_id", "")
            request_id = payload.get("request_id", "")

            user_rate_key = f"user:train:schedule:create:{user_id}"
            user_allowed_request = await rate_limiter.check_window_limit(
                key=user_rate_key,
                limit=settings.MASTERDATA_SCHEDULE_CREATE_USER_RATE_LIMIT,
                window=settings.MASTERDATA_SCHEDULE_CREATE_USER_RATE_WINDOW_SECONDS,
            )
            if not user_allowed_request:
                return standardize_response(
                    status_code=429,
                    messages=["Too many train schedule create requests. Please try again later."],
                )
            
            # train must exist
            train_details = await self.masterdata_repo.get_train_by_id(train_id=train_id)
            if not train_details:
                return standardize_response(
                    status_code=400,
                    messages=[f"Train {train_id} does not exist"],
                )

            # route must exist for this train
            route = await self.masterdata_repo.get_route_by_train_id(train_id=train_id)
            if not route:
                return standardize_response(
                    status_code=400,
                    messages=[f"Route does not exist for train {train_id}"],
                )

            # route stations must exist
            route_stations = await self.masterdata_repo.get_route_stations_by_route_id(route_id=route.id)
            if not route_stations:
                return standardize_response(
                    status_code=400,
                    messages=[f"Route stations not found for train {train_id}"],
                )

            # fetching train-seats details
            train_seats = await self.masterdata_repo.get_train_seats_by_train_id(
                train_id=train_id
            )

            # fetching stations details
            station_ids = [rs.station_id for rs in route_stations]
            station_list_details = await self.masterdata_repo.get_station_by_station_ids(station_ids=station_ids)
            station_map = {station.id: station for station in station_list_details}
            for rs in route_stations:
                station = station_map.get(rs.station_id, None)
                if station:
                    rs.name = station.name
                    rs.code = station.code
                    rs.city = station.city
                    rs.state = station.state
                    
            # validate route station integrity
            self._validate_route_stations(route_stations=route_stations)
            
            # create schedule
            schedule = await self.masterdata_repo.create_schedule(
                train_id=train_id,
                departure_date=departure_date,
                status="A",
            )

            # create outbox event
            await self.outbox_repo.add_outbox_event(
                aggregate_type="SCHEDULES",
                aggregate_id=str(schedule.id),
                event_type=self.OUTBOX_EVENT_SCHEDULE_CREATED,
                payload_json={
                    "schedule_id": schedule.id,
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
                            "name" : rs.name,
                            "code" : rs.code,
                            "city" : rs.city,
                            "state" : rs.state,
                            "sequence_number": rs.sequence_number,
                            "arrival_time": rs.arrival_time.strftime("%H:%M:%S"),
                            "departure_time": rs.departure_time.strftime("%H:%M:%S"),
                            "distance_from_origin": float(rs.distance_from_origin),
                            "status": rs.status,
                        }
                        for rs in route_stations
                    ],
                    "departure_date": str(schedule.departure_date),
                    "status": schedule.status,
                    "event_type": self.OUTBOX_EVENT_SCHEDULE_CREATED,
                    "event_version": 1,
                    "created_by_user_id": user_id,
                    "correlation_id": correlation_id,
                    "request_id": request_id,
                    "event_created_at": str(now_ist()),
                },
                status=self.OUTBOX_STATUS_PENDING,
            )

            await self._db_session.commit()

            return standardize_response(
                status_code=201,
                messages=[f"Train schedule created successfully"],
                data={
                    "schedule_id": schedule.id,
                    "train_id": schedule.train_id,
                    "departure_date": str(schedule.departure_date),
                    "status": schedule.status,
                    "dispatch_status": "accepted",
                }
            )

        except IntegrityError as ex:
            await self._db_session.rollback()
            msg = str(getattr(ex, "orig", ex)).lower()
            return standardize_response(
                status_code=400,
                messages=[f"Unable to create train schedule due to data constraint violation. {msg}"],
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
        

    def _validate_route_stations(self, *, route_stations: list) -> None:

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
