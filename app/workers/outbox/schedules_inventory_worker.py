
import asyncio
from app.infrastructure.outbox.dispatchers.schedules_inventory_dispatcher import run_worker


if __name__ == "__main__":
    asyncio.run(run_worker())
