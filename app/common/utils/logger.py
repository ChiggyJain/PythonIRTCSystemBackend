
"""
Logger System (Enterprise)

Uses loguru.

Features:
---------
- console logging
- file logging
- rotation
- multi-worker safe
- async safe
- reusable
- singleton style usage
"""

from pathlib import Path
from loguru import logger


# =========================================================
# Log directory
# =========================================================

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


LOG_FILE = LOG_DIR / "app.log"


# =========================================================
# Remove default logger
# =========================================================

logger.remove()


# =========================================================
# Console logger
# =========================================================

logger.add(
    sink=lambda msg: print(msg, end=""),
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
)


# =========================================================
# File logger
# =========================================================

logger.add(
    LOG_FILE,
    level="INFO",
    rotation="10 MB",
    retention="10 days",
    compression="zip",
    enqueue=True,  # multi-worker safe
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
)


# =========================================================
# Export logger
# =========================================================

app_logger = logger