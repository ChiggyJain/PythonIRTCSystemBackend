
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.settings import get_settings
from app.core.settings import get_settings
from app.middlewares.exception_middleware import ExceptionMiddleware
from app.core.exception_handlers import register_exception_handlers
from app.core.response import standardize_response
from app.infrastructure.elasticsearch.client import build_elasticsearch_client
from app.core.exceptions import BaseAppException


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.es_client_instances = build_elasticsearch_client()
    try:
        yield
    finally:
        # graceful close
        await app.state.es_client_instances.close()


# Create App
app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
)


# Middleware
app.add_middleware(ExceptionMiddleware)


# Exception Handlers
register_exception_handlers(app)


# Routers (future)
from app.api.v1.router import router as v1_router
app.include_router(v1_router, prefix="/api/v1")



@app.get("/health")
async def health_check():
    return standardize_response(
        status_code=200,
        messages=["Services running"],
        data={
            "service": settings.APP_NAME
        },
    )


@app.get("/es_health_check")
async def es_health_check():
    try:
        await app.state.es_client_instances.client.ping()
        return standardize_response(
            status_code=200,
            messages=["Elasticsearch services ready"],
            data={
                "ready": True
            },            
        )
    except Exception:
        raise BaseAppException(
            status_code=503,
            messages=["Elasticsearch services not reachable"],
        )