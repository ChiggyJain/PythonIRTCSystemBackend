
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.session import get_db
from app.domains.inventory.services.inventory_services import InventoryService


def get_inventory_service(
    db_session: AsyncSession = Depends(get_db),
) -> InventoryService:
    return InventoryService(db_session)