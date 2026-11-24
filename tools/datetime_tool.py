from datetime import datetime, timezone
import zoneinfo
from typing import Dict, Any, Optional

def get_current_datetime(timezone_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Get current date, time, day of week, and timezone.
    If timezone_name is specified (e.g. 'UTC', 'America/New_York', 'Asia/Kolkata'),
    it returns the localized date & time.
    """
    try:
        if timezone_name:
            tz = zoneinfo.ZoneInfo(timezone_name)
            now = datetime.now(tz)
        else:
            now = datetime.now().astimezone()

        return {
            "success": True,
            "iso": now.isoformat(),
            "formatted": now.strftime("%A, %B %d, %Y %I:%M:%S %p %Z"),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "day_of_week": now.strftime("%A"),
            "timezone": str(now.tzinfo),
            "error": None
        }
    except Exception as e:
        # Fallback to local system time
        now = datetime.now().astimezone()
        return {
            "success": True,
            "iso": now.isoformat(),
            "formatted": now.strftime("%A, %B %d, %Y %I:%M:%S %p %Z"),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "day_of_week": now.strftime("%A"),
            "timezone": str(now.tzinfo),
            "warning": f"Timezone error ({str(e)}), used system local timezone instead.",
            "error": None
        }

