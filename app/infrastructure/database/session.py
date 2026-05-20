
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from app.core.settings import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.MYSQL_DB_URL,
    echo=False,  
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    isolation_level="READ COMMITTED",
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session