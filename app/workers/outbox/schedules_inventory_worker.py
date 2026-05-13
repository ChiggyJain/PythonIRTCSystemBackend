
import asyncio
from app.infrastructure.outbox.dispatchers.masterdata_schedules_inventory_dispatcher import run_worker


if __name__ == "__main__":
    asyncio.run(run_worker())
