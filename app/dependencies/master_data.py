
from fastapi import Depends
from app.domains.master_data.stations_service import StationsService
from app.domains.master_data.trains_service import TrainsService
from app.domains.master_data.routes_service import RoutesService
from app.domains.master_data.schedules_service import SchedulesService
from app.domains.master_data.repository.base import MasterDataRepositoryBase
from app.dependencies.repositories import get_master_data_repository


def get_stations_service(
    repo: MasterDataRepositoryBase = Depends(get_master_data_repository),
) -> StationsService:
    return StationsService(repo)


def get_trains_service(
    repo: MasterDataRepositoryBase = Depends(get_master_data_repository),
) -> TrainsService:
    return TrainsService(repo)

def get_routes_service(
    repo: MasterDataRepositoryBase = Depends(get_master_data_repository),
) -> RoutesService:
    return RoutesService(repo)

def get_schedules_service(
    repo: MasterDataRepositoryBase = Depends(get_master_data_repository),
) -> SchedulesService:
    return SchedulesService(repo)