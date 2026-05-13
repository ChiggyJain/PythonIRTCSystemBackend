
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
    KAFKA_PWDCHANGED_OTP_TOPIC: str = "pwdchanged-otp"
    KAFKA_PWDCHANGED_OTP_TOPIC_CONSUMER_GROUP: str = "pwdchanged-otp-consumergrp"
    PWDCHANGED_OTP_OUTBOX_MAX_RETRIES: int = 6

    # password changed related email and sms provider name
    PWDCHANGED_OTP_EMAIL_PROVIDER: str = "SENDGRID"
    PWDCHANGED_OTP_FROM_EMAIL: str = "cjain9975@gmail.com"
    PWDCHANGED_OTP_EMAIL_SUBJECT_PREFIX: str = "IRTC Security"
    PWDCHANGED_OTP_SMS_PROVIDER: str = "NONE"

    # email verification related kafka topic and consumer
    KAFKA_EMAILVERIFICATION_OTP_TOPIC: str = "emailverification-otp"
    KAFKA_EMAILVERIFICATION_OTP_TOPIC_CONSUMER_GROUP: str = "emailverification-otp-consumergrp"
    EMAILVERIFICATION_OTP_OUTBOX_MAX_RETRIES: int = 6

    # email verification related email and sms provider name
    EMAILVERIFICATION_OTP_EMAIL_PROVIDER: str = "SENDGRID"
    EMAILVERIFICATION_OTP_FROM_EMAIL: str = "cjain9975@gmail.com"
    EMAILVERIFICATION_OTP_EMAIL_SUBJECT_PREFIX: str = "IRTC Security"
    
    # email changed related kafka topic and consumer
    KAFKA_EMAILCHANGED_OTP_TOPIC: str = "emailchanged-otp"
    KAFKA_EMAILCHANGED_OTP_TOPIC_CONSUMER_GROUP: str = "emailchanged-otp-consumergrp"
    EMAILCHANGED_OTP_OUTBOX_MAX_RETRIES: int = 6
    
    # email changed related email and sms provider name
    EMAILCHANGED_OTP_EMAIL_PROVIDER: str = "SENDGRID"
    EMAILCHANGED_OTP_FROM_EMAIL: str = "cjain9975@gmail.com"
    EMAILCHANGED_OTP_EMAIL_SUBJECT_PREFIX: str = "IRTC Security"

    # password change OTP request rate limitter
    PWDCHANGED_OTP_API_RATE_LIMIT_REQUEST: int = 5
    PWDCHANGED_OTP_API_RATE_WINDOW_SECONDS: int = 60

    # password chnage confirm OTP request rate limitter
    PWDCHANGED_CONFIRM_API_RATE_LIMIT_REQUEST: int = 5
    PWDCHANGED_CONFIRM_API_RATE_WINDOW_SECONDS: int = 60

    # email verification OTP request rate limitter
    EMAILVERIFICATION_OTP_API_RATE_LIMIT_REQUEST: int = 5
    EMAILVERIFICATION_OTP_API_RATE_WINDOW_SECONDS: int = 60

    # email verification confirm OTP request rate limitter
    EMAILVERIFICATION_CONFIRM_API_RATE_LIMIT_REQUEST: int = 5
    EMAILVERIFICATION_CONFIRM_API_RATE_WINDOW_SECONDS: int = 60

    # email change OTP request rate limitter
    EMAILCHANGE_OTP_API_RATE_LIMIT_REQUEST: int = 5
    EMAILCHANGE_OTP_API_RATE_WINDOW_SECONDS: int = 60

    # email change confirm OTP request rate limitter
    EMAILCHANGE_CONFIRM_API_RATE_LIMIT_REQUEST: int = 5
    EMAILCHANGE_CONFIRM_API_RATE_WINDOW_SECONDS: int = 60

    # admin station create request rate limitter
    STATION_CREATE_API_RATE_LIMIT_REQUEST: int = 10
    STATION_CREATE_API_RATE_WINDOW_SECONDS: int = 60

    # admin train create request rate limitter
    TRAIN_CREATE_API_RATE_LIMIT_REQUEST: int = 10
    TRAIN_CREATE_API_RATE_WINDOW_SECONDS: int = 60

    # admin route create request rate limitter
    ROUTE_CREATE_API_RATE_LIMIT_REQUEST: int = 10
    ROUTE_CREATE_API_RATE_WINDOW_SECONDS: int = 60

    # admin schedule create request rate limitter
    SCHEDULE_CREATE_API_RATE_LIMIT_REQUEST: int = 10
    SCHEDULE_CREATE_API_RATE_WINDOW_SECONDS: int = 60

    # Station KAFKA TOPIC and CONSUMER
    KAFKA_STATION_CREATED_TOPIC: str = "station-created"
    KAFKA_STATION_CREATED_TOPIC_CONSUMER_GROUP: str = "station-events-consumergrp"
    STATION_OUTBOX_MAX_RETRIES: int = 6

    # Train KAFKA TOPIC and CONSUMER
    KAFKA_TRAIN_CREATED_TOPIC: str = "train-created"
    KAFKA_TRAIN_CREATED_TOPIC_CONSUMER_GROUP: str = "train-created-consumergrp"
    TRAIN_OUTBOX_MAX_RETRIES: int = 6
    
    # Route KAFKA TOPIC and CONSUMER
    KAFKA_ROUTE_CREATED_TOPIC: str = "route-created"
    KAFKA_ROUTE_CREATED_TOPIC_CONSUMER_GROUP: str = "route-created-consumergrp"
    ROUTE_OUTBOX_MAX_RETRIES: int = 6
    
    # Schedule KAFKA TOPIC and CONSUMER
    KAFKA_SCHEDULE_CREATED_TOPIC: str = "schedule-created"
    KAFKA_SCHEDULE_CREATED_TOPIC_CONSUMER_GROUP: str = "schedule-created-consumergrp"
    KAFKA_SCHEDULE_INVENTORY_CONSUMER_GROUP: str = "schedule-inventory-consumergrp"
    SCHEDULE_OUTBOX_MAX_RETRIES: int = 6

    # masterdata schedule-inventory seat availability update topic and consumer
    KAFKA_SCHEDULE_INVENTORY_SEAT_AVAILABILITY_UPDATED_TOPIC: str ="schedule-inventory-seat-availability-updated"
    KAFKA_SCHEDULE_INVENTORY_SEAT_AVAILABILITY_UPDATED_TOPIC_CONSUMER_GROUP: str ="schedule-inventory-seat-availability-updated-consumergrp"
    KAFKA_SCHEDULE_INVENTORY_SEAT_AVAILABILITY_UPDATED_TOPIC_OUTBOX_MAX_RETRIES: int =6

    # ELASTICSEARCH CONFIG
    ELASTICSEARCH_URL: str = "http://127.0.0.1:9200"
    ELASTICSEARCH_USERNAME: str | None = None
    ELASTICSEARCH_PASSWORD: str | None = None
    ELASTICSEARCH_VERIFY_CERTS: bool = False
    ELASTICSEARCH_REQUEST_TIMEOUT_SECONDS: int = 10
    ELASTICSEARCH_STATIONS_INDEX: str = "stations"
    ELASTICSEARCH_ROUTES_INDEX: str = "routes"

    # booking config
    BOOKING_TTL_SECONDS: int = 600
    BOOKING_EXPIRY_CHECK_INTERVAL_MS: int = 30000
    LOCK_TTL_SECONDS: int = 600

    # payment gateway service provider config
    PAYMENT_GATEWAY_SERVICE_PROVIDER: str = "razorpay"

    # internal service communication url
    INTERNAL_SERVICE_KEY: str ="irtc-internal-service-key-2026"
    INVENTORY_SERVICE_BASE_URL: str ="http://127.0.0.1:8000"
    PAYMENT_SERVICE_BASE_URL: str ="http://127.0.0.1:8000"


    KAFKA_BOOKING_PAYMENT_SUCCESS_TOPIC: str = "payment-success"
    KAFKA_BOOKING_PAYMENT_FAILED_TOPIC: str = "payment-failed"
    KAFKA_BOOKING_PAYMENT_SUCCESSFAILED_TOPIC_CONSUMER_GROUP: str = "payment-successfailed-consumergrp"
    KAFKA_BOOKING_PAYMENT_SUCCESSFAILED_OUTBOX_MAX_RETRIES: int = 6
    
    
    # Pydantic Settings Config
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )



@lru_cache()
def get_settings() -> Settings:
    return Settings()