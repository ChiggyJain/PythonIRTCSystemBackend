
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
    filter=lambda record: record["extra"].get("log_console", True),
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
    filter=lambda record: record["extra"].get("log_file", True),
)


# =========================================================
# Export logger
# =========================================================

app_logger = logger


# =========================================================
# Flexible log function
# =========================================================

def log_message(
    message: str,
    logging_config={}
):
    """
    Flexible logging using loguru.
    console → print to console
    file → write to file
    """

    app_logger.bind(
        log_console=logging_config['console'],
        log_file=logging_config['file'],
    ).info(message)