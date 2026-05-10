
from fastapi import APIRouter
from app.api.v1.users import router as users_router
from app.api.v1.auth import router as auth_router
from app.api.v1.admin_master_data import router as admin_master_data_router
from app.api.v1.search_discovery import router as search_discovery_router
from app.api.v1.inventory import router as inventory_router
from app.api.v1.bookings import router as booking_router
from app.api.v1.payments import router as payment_router

router = APIRouter()


router.include_router(
    users_router,
    prefix="/users",
    tags=["Users"],
)

router.include_router(
    auth_router,
    prefix="/auth",
    tags=["Users"],
)

router.include_router(
    admin_master_data_router,
    prefix="/admin/master-data",
    tags=["Admin Master Data"],
)

router.include_router(
    search_discovery_router,
    tags=["Search Discovery"],
)

router.include_router(
    inventory_router,
    prefix="/inventory",
)

router.include_router(
    booking_router,
    prefix="/bookings",
)

router.include_router(
    payment_router,
    prefix="/payments",
)