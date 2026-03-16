
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
    Returns IST datetime WITHOUT timezone (naive)
    """

    return datetime.now(IST).replace(tzinfo=None)


# =========================================================
# current IST date
# =========================================================

def today_ist():
    """
    Returns current date in IST
    """

    return now_ist().date()