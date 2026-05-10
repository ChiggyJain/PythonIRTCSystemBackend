
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


class StationsService:

    OUTBOX_STATUS_PENDING = "PENDING"
    OUTBOX_EVENT_STATION_CREATED = "MASTERDATA_STATION_CREATED"

    def __init__(self, db_session: AsyncSession):
        self._db_session = db_session
        self.masterdata_repo = MasterDataSQLAlchemyRepository(db_session)
        self.outbox_repo = OutboxEventsSQLAlchemyRepository(db_session)


    async def create_station(
        self,
        *,
        payload: dict
    ) -> dict:


        try:
            
            # extracted parameters
            user_id = payload.get("user_id", 0)
            name = payload.get("name", "")
            code = payload.get("code", "")
            city = payload.get("city", "")
            state = payload.get("state", "")
            correlation_id = payload.get("correlation_id", "")
            request_id = payload.get("request_id", "")
            code = (code or "").strip().upper()

            # user-level limiter
            user_rate_key = f"user:stations:create:{user_id}"
            user_allowed_request = await rate_limiter.check_window_limit(
                key=user_rate_key,
                limit=settings.MASTERDATA_STATION_CREATE_USER_RATE_LIMIT,
                window=settings.MASTERDATA_STATION_CREATE_USER_RATE_WINDOW_SECONDS,
            )
            if not user_allowed_request:
                return standardize_response(
                    status_code=429,
                    messages=["Too many station create requests. Please try again later."],
                )

            # creating entries into stations
            station = await self.masterdata_repo.create_station(
                name=name,
                code=code,
                city=city,
                state=state,
                status="A",
            )

            # creating entries into outbox events
            await self.outbox_repo.add_outbox_event(
                aggregate_type="STATIONS",
                aggregate_id=str(station.id),
                event_type=self.OUTBOX_EVENT_STATION_CREATED,
                payload_json={
                    "station_id": station.id,
                    "name": station.name,
                    "code": station.code,
                    "city": station.city,
                    "state": station.state,
                    "status": station.status,
                    "created_at": str(station.created_at),
                    "event_type": self.OUTBOX_EVENT_STATION_CREATED,
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
                messages=[f"Station created successfully"],
                data={
                    "id": station.id,
                    "name": station.name,
                    "code": station.code,
                    "city": station.city,
                    "state": station.state,
                    "status": station.status,
                    "dispatch_status": "accepted",
                }
            )
        
        except IntegrityError:
            await self._db_session.rollback()
            return standardize_response(
                status_code=400,
                messages=["Station code already exists"],
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

        
