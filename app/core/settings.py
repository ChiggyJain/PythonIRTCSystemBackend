
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    
    # app config
    APP_NAME: str = "IRTC Backend"
    APP_ENV: str = "local"
    APP_DEBUG: bool = True
    
    # jwt config
    JWT_SECRET_KEY: str
    TOKEN_HASH_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_EXPIRE_DAYS: int = 7
    JWT_ISSUER: str = "irtc-backend"
    JWT_AUDIENCE: str = "irtc-users"
    
    # cache profile ttl seconds
    USER_PROFILE_CACHE_TTL_SECONDS: int = 300

    # email service provider key config
    SENDGRID_API_KEY: str

    # mysql db config
    MYSQL_DB_HOST: str
    MYSQL_DB_PORT: int
    MYSQL_DB_NAME: str
    MYSQL_DB_USER: str
    MYSQL_DB_PASSWORD: str

    # redis config
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int

    # kafka config
    KAFKA_BOOTSTRAP_SERVERS : str
    KAFKA_CLIENT_ID: str = "irtc-backend"
    
    # password changed related kafka topic and consumer
    PWDCHANGED_OTP_DISPATCH_TOPIC: str = "pwdchanged-otp-dispatch"
    PWDCHANGED_OTP_DISPATCH_CONSUMER_GROUP: str = "pwdchanged-otp-dispatch-consumergrp-1"
    PWDCHANGED_OTP_OUTBOX_MAX_RETRIES: int = 6

    # password changed related email and sms provider name
    PWDCHANGED_OTP_EMAIL_PROVIDER: str = "SENDGRID"
    PWDCHANGED_OTP_FROM_EMAIL: str = "cjain9975@gmail.com"
    PWDCHANGED_OTP_EMAIL_SUBJECT_PREFIX: str = "IRTC Security"
    PWDCHANGED_OTP_SMS_PROVIDER: str = "NONE"

    # email verification related kafka topic and consumer
    EMAILVERIFICATION_OTP_DISPATCH_TOPIC: str = "emailverification-otp-dispatch"
    EMAILVERIFICATION_OTP_DISPATCH_CONSUMER_GROUP: str = "emailverification-otp-dispatch-consumergrp-1"
    EMAILVERIFICATION_OTP_OUTBOX_MAX_RETRIES: int = 6

    # email verification related email and sms provider name
    EMAILVERIFICATION_OTP_EMAIL_PROVIDER: str = "SENDGRID"
    EMAILVERIFICATION_OTP_FROM_EMAIL: str = "cjain9975@gmail.com"
    EMAILVERIFICATION_OTP_EMAIL_SUBJECT_PREFIX: str = "IRTC Security"
    
    # email changed related kafka topic and consumer
    EMAILCHANGED_OTP_DISPATCH_TOPIC: str = "emailchanged-otp-dispatch"
    EMAILCHANGED_OTP_DISPATCH_CONSUMER_GROUP: str = "emailchanged-otp-dispatch-consumergrp-1"
    EMAILCHANGED_OTP_OUTBOX_MAX_RETRIES: int = 6
    
    # email changed related email and sms provider name
    EMAILCHANGED_OTP_EMAIL_PROVIDER: str = "SENDGRID"
    EMAILCHANGED_OTP_FROM_EMAIL: str = "cjain9975@gmail.com"
    EMAILCHANGED_OTP_EMAIL_SUBJECT_PREFIX: str = "IRTC Security"

    # password change OTP request rate limitter
    PWDCHANGED_OTP_USER_RATE_LIMIT: int = 5
    PWDCHANGED_OTP_USER_RATE_WINDOW_SECONDS: int = 60

    # password chnage confirm OTP request rate limitter
    PWDCHANGED_CONFIRM_USER_RATE_LIMIT: int = 5
    PWDCHANGED_CONFIRM_USER_RATE_WINDOW_SECONDS: int = 60

    # email verification OTP request rate limitter
    EMAILVERIFICATION_OTP_USER_RATE_LIMIT: int = 5
    EMAILVERIFICATION_OTP_USER_RATE_WINDOW_SECONDS: int = 60

    # email verification confirm OTP request rate limitter
    EMAILVERIFICATION_CONFIRM_USER_RATE_LIMIT: int = 5
    EMAILVERIFICATION_CONFIRM_USER_RATE_WINDOW_SECONDS: int = 60

    # email change OTP request rate limitter
    EMAILCHANGE_OTP_USER_RATE_LIMIT: int = 5
    EMAILCHANGE_OTP_USER_RATE_WINDOW_SECONDS: int = 60

    # email change confirm OTP request rate limitter
    EMAILCHANGE_CONFIRM_USER_RATE_LIMIT: int = 5
    EMAILCHANGE_CONFIRM_USER_RATE_WINDOW_SECONDS: int = 60

    # admin station create request rate limitter
    MASTERDATA_STATION_CREATE_USER_RATE_LIMIT: int = 10
    MASTERDATA_STATION_CREATE_USER_RATE_WINDOW_SECONDS: int = 60

    # admin train create request rate limitter
    MASTERDATA_TRAIN_CREATE_USER_RATE_LIMIT: int = 10
    MASTERDATA_TRAIN_CREATE_USER_RATE_WINDOW_SECONDS: int = 60

    # admin route create request rate limitter
    MASTERDATA_ROUTE_CREATE_USER_RATE_LIMIT: int = 10
    MASTERDATA_ROUTE_CREATE_USER_RATE_WINDOW_SECONDS: int = 60

    # admin schedule create request rate limitter
    MASTERDATA_SCHEDULE_CREATE_USER_RATE_LIMIT: int = 10
    MASTERDATA_SCHEDULE_CREATE_USER_RATE_WINDOW_SECONDS: int = 60

    # Station KAFKA TOPIC and CONSUMER
    MASTERDATA_STATION_CREATED: str = "masterdata-station-created"
    MASTERDATA_STATION_CONSUMER_GROUP: str = "masterdata-station-events-dispatch-consumergrp-1"
    MASTERDATA_STATION_OUTBOX_MAX_RETRIES: int = 6

    # Train KAFKA TOPIC and CONSUMER
    MASTERDATA_TRAIN_CREATED: str = "masterdata-train-created"
    MASTERDATA_TRAIN_CONSUMER_GROUP: str = "masterdata-train-events-dispatch-consumergrp-1"
    MASTERDATA_TRAIN_OUTBOX_MAX_RETRIES: int = 6
    
    # Route KAFKA TOPIC and CONSUMER
    MASTERDATA_ROUTE_CREATED: str = "masterdata-route-created"
    MASTERDATA_ROUTE_CONSUMER_GROUP: str = "masterdata-route-events-dispatch-consumergrp-1"
    MASTERDATA_ROUTE_OUTBOX_MAX_RETRIES: int = 6
    
    # Schedule KAFKA TOPIC and CONSUMER
    MASTERDATA_SCHEDULE_CREATED: str = "masterdata-schedule-created"
    MASTERDATA_SCHEDULE_CONSUMER_GROUP: str = "masterdata-schedule-events-dispatch-consumergrp-1"
    MASTERDATA_SCHEDULE_INVENTORY_CONSUMER_GROUP: str = "masterdata-schedule-events-inventory-consumergrp-1"
    MASTERDATA_SCHEDULE_OUTBOX_MAX_RETRIES: int = 6
        
    # ELASTICSEARCH CONFIG
    ELASTICSEARCH_URL: str = "http://127.0.0.1:9200"
    ELASTICSEARCH_USERNAME: str | None = None
    ELASTICSEARCH_PASSWORD: str | None = None
    ELASTICSEARCH_VERIFY_CERTS: bool = False
    ELASTICSEARCH_REQUEST_TIMEOUT_SECONDS: int = 10
    ELASTICSEARCH_STATIONS_INDEX: str = "stations"
    ELASTICSEARCH_ROUTES_INDEX: str = "routes_v1"

    # booking config
    BOOKING_TTL_SECONDS: int = 600
    BOOKING_EXPIRY_CHECK_INTERVAL_MS: int = 30000
    LOCK_TTL_SECONDS: int = 600

    # internal service communication url
    INTERNAL_SERVICE_KEY: str ="irtc-internal-service-key-2026"
    INVENTORY_SERVICE_URL: str ="http://127.0.0.1:8000"
    PAYMENT_SERVICE_URL: str ="http://127.0.0.1:8000"


    
    # Pydantic Settings Config
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )



@lru_cache()
def get_settings() -> Settings:
    return Settings()