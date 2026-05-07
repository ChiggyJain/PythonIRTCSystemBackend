
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
    return datetime.now(IST).replace(tzinfo=None)

def today_ist():
    return now_ist().date()