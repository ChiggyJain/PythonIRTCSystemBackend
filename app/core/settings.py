
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application Settings

    This class loads environment variables using pydantic-settings.

    Why BaseSettings?
    -----------------
    - Supports .env
    - Supports environment variables
    - Type validation
    - Production safe

    This object should NOT be created multiple times.
    It will be cached using lru_cache (singleton per worker).
    """

    # =========================
    # APP CONFIG
    # =========================

    APP_NAME: str = "IRTC Backend"
    APP_ENV: str = "local"
    APP_DEBUG: bool = True

    # =========================
    # MYSQL CONFIG
    # =========================

    MYSQL_DB_HOST: str
    MYSQL_DB_PORT: int
    MYSQL_DB_NAME: str
    MYSQL_DB_USER: str
    MYSQL_DB_PASSWORD: str

    # =========================
    # REDIS CONFIG
    # =========================

    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int

    # =========================
    # KAFKA CONFIG
    # =========================

    KAFKA_BOOTSTRAP_SERVERS: str

    # =========================
    # SENDGRID CONFIG
    # =========================

    SENDGRID_API_KEY: str

    # =========================
    # JWT Settings
    # =========================

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_EXPIRE_DAYS: int = 7
    JWT_ISSUER: str = "irtc-backend"
    JWT_AUDIENCE: str = "irtc-users"
    

    # =========================
    # Pydantic Settings Config
    # =========================

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )



@lru_cache()
def get_settings() -> Settings:
    """
    Singleton Settings Provider

    Why lru_cache?
    --------------
    - Creates one instance per process
    - Safe for multi-worker
    - Safe for async
    - Safe for FastAPI dependency injection
    - Recommended by FastAPI docs

    Each worker will have its own cached instance.
    """
    return Settings()