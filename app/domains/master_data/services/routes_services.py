
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from decimal import Decimal
from app.common.utils.datetime import now_ist
from app.core.exceptions import BaseAppException
from app.core.response import (
    success_response, 
    error_response,
    exception_response
)
from app.core.settings import get_settings
from app.common.utils.ratelimiter import rate_limiter
from app.domains.master_data.repository.sqlalchemy_repo import MasterDataSQLAlchemyRepository
from app.infrastructure.outbox.repository.sqlalchemy_repo import OutboxEventsSQLAlchemyRepository


settings = get_settings()


class RoutesService:

    OUTBOX_STATUS_PENDING = "PENDING"
    OUTBOX_EVENT_ROUTE_CREATED = "MASTERDATA_ROUTE_CREATED"

    def __init__(self, db_session: AsyncSession):
        self._db_session = db_session
        self.masterdata_repo = MasterDataSQLAlchemyRepository(db_session)
        self.outbox_repo = OutboxEventsSQLAlchemyRepository(db_session)


    async def create_train_route(
        self,
        *,
        payload: dict,
    ) -> dict:
        
        try:

            # extracted parameters
            train_id = int(payload.get("train_id", 0))
            station_details = payload.get("station_details", [])
            user_id = payload.get("user_id", 0)
            correlation_id = payload.get("correlation_id", "")
            request_id = payload.get("request_id", "")

            # user level rate-limitter
            user_rate_key = f"user:train:route:create:{user_id}"
            user_allowed_request = await rate_limiter.check_window_limit(
                key=user_rate_key,
                limit=settings.MASTERDATA_ROUTE_CREATE_USER_RATE_LIMIT,
                window=settings.MASTERDATA_ROUTE_CREATE_USER_RATE_WINDOW_SECONDS,
            )
            if not user_allowed_request:
                return error_response(
                    status_code=429,
                    messages=["Too many train-route create requests. Please try again later."],
                )
            
            # train existence check
            train_details = await self.masterdata_repo.get_train_by_id(train_id=train_id)
            if not train_details:
                return error_response(
                    status_code=400,
                    messages=[f"Train id {train_id} does not exist"],
                )

            # station existence check
            station_ids = [item["station_id"] for item in station_details]
            existing_station_count = await self.masterdata_repo.count_existing_station_ids(station_ids=station_ids)
            if existing_station_count != len(station_ids):
                return error_response(
                    status_code=400,
                    messages=["One or more station_id does not exist"],
                )
            
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
                    "route_status": route.status,
                    "event_type": self.OUTBOX_EVENT_ROUTE_CREATED,
                    "event_version": 1,
                    "created_by_user_id": user_id,
                    "correlation_id": correlation_id,
                    "request_id": request_id,
                    "event_created_at": str(now_ist()),
                },
                status=self.OUTBOX_STATUS_PENDING,
            )

            await self._db_session.commit()

            return success_response(
                status_code=201,
                messages=[f"Train route created successfully"],
                data={
                    "route_id": route.id,
                    "train_id": route.train_id,
                    "status": route.status,
                    "station_details": [
                        {
                            "route_station_id": rs.id,
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
            )
        
        except IntegrityError as ex:
            await self._db_session.rollback()
            msg = str(getattr(ex, "orig", ex)).lower()
            return error_response(
                status_code=400,
                messages=[f"Unable to create train route due to data constraint violation. {msg}"],
            )
        
        except BaseAppException as e:
            await self._db_session.rollback()
            raise e
        
        except Exception as e:
            await self._db_session.rollback()
            return exception_response(
                status_code=500,
                messages=[f"{str(e)}"]
            )