
from fastapi import Depends
from app.domains.master_data.services.stations_service import StationsService
from app.domains.master_data.services.trains_service import TrainsService
from app.domains.master_data.services.routes_service import RoutesService
from app.domains.master_data.services.schedules_service import TrainSchedulesService
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

def get_train_schedules_service(
    repo: MasterDataRepositoryBase = Depends(get_master_data_repository),
) -> TrainSchedulesService:
    return TrainSchedulesService(repo)