
"""
Main Application Entry
Responsible for:
---------------
- Create FastAPI app
- Register middleware
- Register exception handlers
- Register routers
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import APP_NAME
from app.core.settings import get_settings
from app.middlewares.exception_middleware import ExceptionMiddleware
from app.core.exception_handlers import register_exception_handlers
from app.core.response import success_response
from app.infrastructure.elasticsearch.client import build_elasticsearch_client
from app.core.exceptions import BaseAppException




@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    # Hybrid/Eager: create client object at startup (cheap), no hard fail on ES ping here
    app.state.routes_es_client = build_elasticsearch_client(settings.ELASTICSEARCH_ROUTES_INDEX)
    try:
        yield
    finally:
        # graceful close
        await app.state.routes_es_client.close()



# =========================================================
# Create App
# =========================================================

app = FastAPI(
    title=APP_NAME,
    lifespan=lifespan,
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

from app.api.v1.router import router as v1_router
app.include_router(v1_router, prefix="/api/v1")


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


@app.get("/routes_es_client_ready")
async def readiness_check():
    try:
        await app.state.routes_es_client.client.ping()
        return success_response(
            data={"ready": True},
            messages=["Service ready"],
        )
    except Exception:
        raise BaseAppException(
            status_code=503,
            messages=["Elasticsearch not reachable for RoutesES"],
        )