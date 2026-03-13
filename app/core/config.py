
"""
Application Config Builder

This module builds runtime configuration values
from Settings.

Why needed?
-----------
Settings only stores raw env values.
Config builds computed values like:

- Database URL
- Redis URL
- Kafka config
- Other derived configs

This keeps settings clean and reusable.

This module must be safe for:

- multi worker
- async
- singleton usage
"""

from urllib.parse import quote_plus
from app.core.settings import get_settings


# Load settings (singleton per worker)
settings = get_settings()


# =========================================================
# MYSQL CONFIG
# =========================================================

"""
Build MySQL async database URL

We use asyncmy driver for SQLAlchemy async engine.

Format:
mysql+asyncmy://user:password@host:port/dbname
"""

MYSQL_PASSWORD = quote_plus(settings.MYSQL_DB_PASSWORD)
MYSQL_DB_URL: str = (
    f"mysql+asyncmy://"
    f"{settings.MYSQL_DB_USER}:"
    f"{MYSQL_PASSWORD}@"
    f"{settings.MYSQL_DB_HOST}:"
    f"{settings.MYSQL_DB_PORT}/"
    f"{settings.MYSQL_DB_NAME}"
)


# =========================================================
# REDIS CONFIG
# =========================================================

"""
Build Redis URL

Format:
redis://host:port/db
"""

REDIS_URL: str = (
    f"redis://"
    f"{settings.REDIS_HOST}:"
    f"{settings.REDIS_PORT}/"
    f"{settings.REDIS_DB}"
)


# =========================================================
# KAFKA CONFIG
# =========================================================

"""
Kafka bootstrap servers

Example:
127.0.0.1:9092
"""

KAFKA_BOOTSTRAP_SERVERS: str = settings.KAFKA_BOOTSTRAP_SERVERS


# =========================================================
# SENDGRID CONFIG
# =========================================================

"""
SendGrid API Key
"""

SENDGRID_API_KEY: str = settings.SENDGRID_API_KEY


# =========================================================
# APP CONFIG
# =========================================================

APP_NAME: str = settings.APP_NAME
APP_ENV: str = settings.APP_ENV
APP_DEBUG: bool = settings.APP_DEBUG