
from fastapi import APIRouter, Depends, Request
from app.common.decorators.feature_control import feature_control
from app.common.utils.ratelimiter import rate_limiter
from app.core.exceptions import BaseAppException
from app.core.response import success_response
from app.core.routing.feature_route import FeatureAPIRoute
from app.core.settings import get_settings
from app.domains.inventory.services.inventory_services import InventoryService
from app.dependencies.inventory import get_inventory_service



settings = get_settings()
router = APIRouter()


# -------------------------
# stations create process
# -------------------------

@feature_control(
    {
        "name": "v1.inventory.schedules.schedule_id.availability",
        "logging": {
            "console": True,
            "file": True,
        },
        "rate_limit": {
            "limit": 1000,
            "window": 60,
        },
    }
)
async def get_inventory_schedules_availabiliity(
    schedule_id: int,    
    service: InventoryService = Depends(get_inventory_service),
):
    
    return await service.get_inventory_schedules_availabiliity(
        schedule_id
    )

router.add_api_route(
    "/schedules/{schedule_id}/availability",
    get_inventory_schedules_availabiliity,
    methods=["GET"],
    route_class_override=FeatureAPIRoute,
)


