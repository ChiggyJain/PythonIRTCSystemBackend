
"""
Main Application Entry

Responsible for:
---------------
- Create FastAPI app
- Register middleware
- Register exception handlers
- Register routers
"""

from fastapi import FastAPI

from app.core.config import APP_NAME
from app.middlewares.exception_middleware import ExceptionMiddleware
from app.core.exception_handlers import register_exception_handlers
from app.core.response import success_response


# =========================================================
# Create App
# =========================================================

app = FastAPI(
    title=APP_NAME,
)


# =========================================================
# Middleware
# =========================================================

"""
Register exception middleware

Must be before routers
"""

app.add_middleware(ExceptionMiddleware)


# =========================================================
# Exception Handlers
# =========================================================

register_exception_handlers(app)


# =========================================================
# Routers (future)
# =========================================================

# from app.api.v1.router import router as v1_router
# app.include_router(v1_router, prefix="/api/v1")


# =========================================================
# Health Check API
# =========================================================


@app.get("/health")
async def health_check():
    """
    Health check endpoint

    Used for:
    - Load balancer
    - Docker
    - Kubernetes
    - Monitoring
    """

    return success_response(
        data={"service": APP_NAME},
        messages=["Service running"],
    )