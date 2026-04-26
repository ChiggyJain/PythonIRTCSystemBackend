
from fastapi import Depends
from app.domains.master_data.stations_service import StationsService
from app.domains.master_data.repository.base import MasterDataRepositoryBase
from app.dependencies.repositories import get_master_data_repository


def get_stations_service(
    repo: MasterDataRepositoryBase = Depends(get_master_data_repository),
) -> StationsService:
    return StationsService(repo)