
"""
Database Session Manager

This module creates async SQLAlchemy engine and session factory.

Design goals:
-------------
- Async safe
- Multi-worker safe
- Singleton per worker
- Connection pool enabled
- Production safe
- No global session objects
- Compatible with FastAPI dependency injection
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)

from app.core.config import MYSQL_DB_URL


# =========================================================
# ENGINE (created once per worker)
# =========================================================

"""
Create async engine.

Important:
----------
Each worker process will create its own engine.

This is correct behavior.

Do NOT try to share engine across workers.
"""

engine = create_async_engine(
    MYSQL_DB_URL,
    echo=False,  # set True only for debugging
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)


# =========================================================
# SESSION FACTORY
# =========================================================

"""
Session factory.

We create sessionmaker instead of session.

Each request will create new session.
"""

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# =========================================================
# Dependency for FastAPI
# =========================================================

"""
FastAPI dependency.

Usage:
------
Depends(get_db)

Creates new session per request.
Closes after request.

Safe for async.
Safe for multi-worker.
"""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session