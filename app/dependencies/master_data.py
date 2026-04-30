
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.session import get_db
from app.domains.master_data.services.stations_services import StationsService
from app.domains.master_data.services.trains_services import TrainsService
from app.domains.master_data.services.routes_services import RoutesService
from app.domains.master_data.services.schedules_services import TrainSchedulesService

def get_stations_service(
    db_session: AsyncSession = Depends(get_db),
) -> StationsService:
    return StationsService(db_session)

def get_trains_service(
    db_session: AsyncSession = Depends(get_db),
) -> TrainsService:
    return TrainsService(db_session)

def get_routes_service(
    db_session: AsyncSession = Depends(get_db),
) -> RoutesService:
    return RoutesService(db_session)

def get_train_schedules_service(
    db_session: AsyncSession = Depends(get_db),
) -> TrainSchedulesService:
    return TrainSchedulesService(db_session)