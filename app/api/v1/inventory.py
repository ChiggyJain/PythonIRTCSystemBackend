
from fastapi import APIRouter, Depends, Request, Query
from typing import List
from app.common.decorators.feature_control import feature_control
from app.core.routing.feature_route import FeatureAPIRoute
from app.core.settings import get_settings
from app.domains.inventory.services.inventory_services import InventoryService
from app.dependencies.inventory import get_inventory_service


settings = get_settings()
router = APIRouter()


@feature_control(
    {
        "name": "inventory:schedule:availability",
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
async def get_inventory_schedule_availabiliity(
    schedule_id: int,    
    service: InventoryService = Depends(get_inventory_service),
):
    return await service.get_inventory_schedule_availabiliity(schedule_id=schedule_id)

router.add_api_route(
    "/schedules/{schedule_id}/availability",
    get_inventory_schedule_availabiliity,
    methods=["GET"],
    route_class_override=FeatureAPIRoute,
)


@feature_control(
    {
        "name": "inventory:schedule:seats:availability",
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
async def get_inventory_schedules_seats_availabiliity(
    schedule_id: int,    
    seat_ids: str = Query(...),
    from_station_sequence_number: int = Query(...),
    to_station_sequence_number: int = Query(...),
    service: InventoryService = Depends(get_inventory_service),
):
    return await service.get_inventory_schedule_seats_availabiliity(
        schedule_id=schedule_id, 
        seat_ids=[
            int(seat_id.strip())
            for seat_id in seat_ids.split(",")
        ],
        from_station_sequence_number=from_station_sequence_number, 
        to_station_sequence_number=to_station_sequence_number
    )

router.add_api_route(
    "/schedules/{schedule_id}/seats",
    get_inventory_schedules_seats_availabiliity,
    methods=["GET"],
    route_class_override=FeatureAPIRoute,
)


