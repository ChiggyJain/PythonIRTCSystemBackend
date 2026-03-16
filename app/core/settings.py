
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
    # KAFKA APP CONFIG
    # =========================

    KAFKA_BOOTSTRAP_SERVERS : str
    KAFKA_CLIENT_ID: str = "irtc-backend"

    # currently not in use
    PWDCHANGED_OTP_DISPATCH_TOPIC: str = "pwdchanged-otp-dispatch-v1"
    PWDCHANGED_OTP_DISPATCH_CONSUMER_GROUP: str = "pwdchanged-otp-dispatch-consumer-v1"
    PWDCHANGED_OTP_OUTBOX_MAX_RETRIES: int = 6

    # my suggestion for password_changed otp concept
    PWDCHANGED_OTP_DISPATCH_TOPIC: str = "pwdchanged-otp-dispatch-v1"
    PWDCHANGED_OTP_DISPATCH_CONSUMER_GROUP: str = "pwdchanged-pwdchanged-otp-dispatch-consumer-v1"
    PWDCHANGED_OTP_OUTBOX_MAX_RETRIES: int = 6

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
    # OTP PROVIDER CONFIG
    # =========================

    # currently not in use
    PWDCHANGED_OTP_EMAIL_PROVIDER: str = "SENDGRID"
    PWDCHANGED_OTP_SMS_PROVIDER: str = "NONE"
    PWDCHANGED_OTP_FROM_EMAIL: str = "cjain9975@gmail.com"
    PWDCHANGED_OTP_EMAIL_SUBJECT_PREFIX: str = "IRTC Security"

    # my suggestion for password_changed otp concept
    PWDCHANGED_OTP_EMAIL_PROVIDER: str = "SENDGRID"
    PWDCHANGED_OTP_SMS_PROVIDER: str = "NONE"
    PWDCHANGED_PWDCHANGED_OTP_FROM_EMAIL: str = "cjain9975@gmail.com"
    PWDCHANGED_OTP_EMAIL_SUBJECT_PREFIX: str = "IRTC Security"


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