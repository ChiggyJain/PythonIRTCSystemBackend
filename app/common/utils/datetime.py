
"""
Datetime Utility (IST)

All datetime in system must use IST timezone.
"""

from datetime import datetime
from zoneinfo import ZoneInfo


# =========================================================
# IST timezone
# =========================================================

IST = ZoneInfo("Asia/Kolkata")


# =========================================================
# current IST datetime
# =========================================================

def now_ist() -> datetime:
    """
    Returns current datetime in IST
    """

    return datetime.now(IST)


# =========================================================
# current IST date
# =========================================================

def today_ist():
    """
    Returns current date in IST
    """

    return now_ist().date()