
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
    
    
    # ============================================
    # PASSWORD CHANGED OTP KAFKA TOPIC and CONSUMER
    # =============================================

    PWDCHANGED_OTP_DISPATCH_TOPIC: str = "pwdchanged-otp-dispatch-v1"
    PWDCHANGED_OTP_DISPATCH_CONSUMER_GROUP: str = "pwdchanged-otp-dispatch-consumer-v1"
    PWDCHANGED_OTP_OUTBOX_MAX_RETRIES: int = 6

    # =========================
    # SENDGRID CONFIG
    # =========================

    SENDGRID_API_KEY: str

    # =========================
    # JWT Settings
    # =========================

    JWT_SECRET_KEY: str
    TOKEN_HASH_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_EXPIRE_DAYS: int = 7
    JWT_ISSUER: str = "irtc-backend"
    JWT_AUDIENCE: str = "irtc-users"
    

    # =======================================================
    # PASSWORD CHANGED OTP SENDER PROVIDER CONFIG (EMAIL, SMS)
    # ========================================================

    PWDCHANGED_OTP_EMAIL_PROVIDER: str = "SENDGRID"
    PWDCHANGED_OTP_FROM_EMAIL: str = "cjain9975@gmail.com"
    PWDCHANGED_OTP_EMAIL_SUBJECT_PREFIX: str = "IRTC Security"
    PWDCHANGED_OTP_SMS_PROVIDER: str = "NONE"


    # =====================================================
    # EMAIL VERIFICATION OTP KAFKA TOPIC and CONSUMER
    # =====================================================

    EMAILVERIFICATION_OTP_DISPATCH_TOPIC: str = "emailverification-otp-dispatch-v1"
    EMAILVERIFICATION_OTP_DISPATCH_CONSUMER_GROUP: str = "emailverification-otp-dispatch-consumer-v1"
    EMAILVERIFICATION_OTP_OUTBOX_MAX_RETRIES: int = 6


    # =====================================================
    # EMAIL VERIFICATION OTP SENDER PROVIDER CONFIG
    # =====================================================

    EMAILVERIFICATION_OTP_EMAIL_PROVIDER: str = "SENDGRID"
    EMAILVERIFICATION_OTP_FROM_EMAIL: str = "cjain9975@gmail.com"
    EMAILVERIFICATION_OTP_EMAIL_SUBJECT_PREFIX: str = "IRTC Security"
    

    # =====================================================
    # EMAIL CHANGED OTP KAFKA TOPIC and CONSUMER
    # =====================================================
    EMAILCHANGED_OTP_DISPATCH_TOPIC: str = "emailchanged-otp-dispatch-v1"
    EMAILCHANGED_OTP_DISPATCH_CONSUMER_GROUP: str = "emailchanged-otp-dispatch-consumer-v1"
    EMAILCHANGED_OTP_OUTBOX_MAX_RETRIES: int = 6

    # =====================================================
    # EMAIL CHANGED OTP SENDER PROVIDER CONFIG (EMAIL only)
    # =====================================================
    EMAILCHANGED_OTP_EMAIL_PROVIDER: str = "SENDGRID"
    EMAILCHANGED_OTP_FROM_EMAIL: str = "cjain9975@gmail.com"
    EMAILCHANGED_OTP_EMAIL_SUBJECT_PREFIX: str = "IRTC Security"

    # User-based rate limit for password change OTP request API
    PWDCHANGED_OTP_USER_RATE_LIMIT: int = 5
    PWDCHANGED_OTP_USER_RATE_WINDOW_SECONDS: int = 60

    # User-based rate limit for password change confirm API
    PWDCHANGED_CONFIRM_USER_RATE_LIMIT: int = 5
    PWDCHANGED_CONFIRM_USER_RATE_WINDOW_SECONDS: int = 60


    # User-based rate limit for email verfication OTP request API
    EMAILVERIFICATION_OTP_USER_RATE_LIMIT: int = 5
    EMAILVERIFICATION_OTP_USER_RATE_WINDOW_SECONDS: int = 60

    # User-based rate limit for email verfication confirm API
    EMAILVERIFICATION_CONFIRM_USER_RATE_LIMIT: int = 5
    EMAILVERIFICATION_CONFIRM_USER_RATE_WINDOW_SECONDS: int = 60

    # User-based rate limit for email verfication OTP request API
    EMAILCHANGE_OTP_USER_RATE_LIMIT: int = 5
    EMAILCHANGE_OTP_USER_RATE_WINDOW_SECONDS: int = 60

    # User-based rate limit for email verfication confirm API
    EMAILCHANGE_CONFIRM_USER_RATE_LIMIT: int = 5
    EMAILCHANGE_CONFIRM_USER_RATE_WINDOW_SECONDS: int = 60

    
    # Station KAFKA TOPIC and CONSUMER
    MASTERDATA_STATION_EVENT_TOPIC: str = "masterdata-station-events-v1"
    MASTERDATA_STATION_CONSUMER_GROUP: str = "masterdata-station-events-dispatch-consumer-v1"
    MASTERDATA_STATION_OUTBOX_MAX_RETRIES: int = 6
    MASTERDATA_STATION_CREATE_USER_RATE_LIMIT: int = 10
    MASTERDATA_STATION_CREATE_USER_RATE_WINDOW_SECONDS: int = 60

    # Train KAFKA TOPIC and CONSUMER
    MASTERDATA_TRAIN_EVENT_TOPIC: str = "masterdata-train-events-v1"
    MASTERDATA_TRAIN_CONSUMER_GROUP: str = "masterdata-train-events-dispatch-consumer-v1"
    MASTERDATA_TRAIN_OUTBOX_MAX_RETRIES: int = 6
    MASTERDATA_TRAIN_CREATE_USER_RATE_LIMIT: int = 10
    MASTERDATA_TRAIN_CREATE_USER_RATE_WINDOW_SECONDS: int = 60

    # Route KAFKA TOPIC and CONSUMER
    MASTERDATA_ROUTE_EVENT_TOPIC: str = "masterdata-route-events-v1"
    MASTERDATA_ROUTE_CONSUMER_GROUP: str = "masterdata-route-events-dispatch-consumer-v1"
    MASTERDATA_ROUTE_OUTBOX_MAX_RETRIES: int = 6
    MASTERDATA_ROUTE_CREATE_USER_RATE_LIMIT: int = 10
    MASTERDATA_ROUTE_CREATE_USER_RATE_WINDOW_SECONDS: int = 60

    # Schedule KAFKA TOPIC and CONSUMER
    MASTERDATA_SCHEDULE_EVENT_TOPIC: str = "masterdata-schedule-events-v1"
    MASTERDATA_SCHEDULE_CONSUMER_GROUP: str = "masterdata-schedule-events-dispatch-consumer-v1"
    MASTERDATA_SCHEDULE_OUTBOX_MAX_RETRIES: int = 6
    MASTERDATA_SCHEDULE_CREATE_USER_RATE_LIMIT: int = 10
    MASTERDATA_SCHEDULE_CREATE_USER_RATE_WINDOW_SECONDS: int = 60
    
    
    # ELASTICSEARCH CONFIG
    ELASTICSEARCH_URL: str = "http://127.0.0.1:9200"
    ELASTICSEARCH_USERNAME: str | None = None
    ELASTICSEARCH_PASSWORD: str | None = None
    ELASTICSEARCH_VERIFY_CERTS: bool = False
    ELASTICSEARCH_REQUEST_TIMEOUT_SECONDS: int = 10

    # Station index in Elasticsearch
    ELASTICSEARCH_STATIONS_INDEX: str = "stations_v1"
    

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