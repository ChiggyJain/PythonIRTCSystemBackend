
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.common.utils.datetime import now_ist
from app.core.exceptions import BaseAppException
from app.domains.master_data.repository.sqlalchemy_repo import MasterDataSQLAlchemyRepository
from app.infrastructure.outbox.repository.sqlalchemy_repo import OutboxEventsSQLAlchemyRepository


class StationsService:

    OUTBOX_STATUS_PENDING = "PENDING"
    OUTBOX_EVENT_STATION_CREATED = "MASTERDATA_STATION_CREATED_V1"

    def __init__(self, db_session: AsyncSession):
        self._db_session = db_session
        self.masterdata_repo = MasterDataSQLAlchemyRepository(db_session)
        self.outbox_repo = OutboxEventsSQLAlchemyRepository(db_session)


    async def create_station(
        self,
        *,
        name: str,
        code: str,
        city: str,
        state: str,
        admin_user_id: int,
        correlation_id: str | None = None,
        request_id: str | None = None,
    ) -> dict:

        code = (code or "").strip().upper()

        try:

            # creating entries into station
            station = await self.masterdata_repo.create_station(
                name=name,
                code=code,
                city=city,
                state=state,
                status="A",
            )

            # creating entries into outbox
            await self.outbox_repo.add_outbox_event(
                aggregate_type="STATION",
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
                    "created_by_admin_user_id": admin_user_id,
                    "correlation_id": correlation_id,
                    "request_id": request_id,
                    "event_created_at": str(now_ist()),
                },
                status=self.OUTBOX_STATUS_PENDING,
            )

            # committing the records at db level
            await self._db_session.commit()

        except IntegrityError:
            # rollback is happening here if station-code is duplicate
            await self._db_session.rollback()
            raise BaseAppException(
                status_code=400,
                messages=["Station code already exists"],
            )
        except Exception:
            await self._db_session.rollback()
            raise

        return {
            "id": station.id,
            "name": station.name,
            "code": station.code,
            "city": station.city,
            "state": station.state,
            "status": station.status,
            "dispatch_status": "accepted",
        }
