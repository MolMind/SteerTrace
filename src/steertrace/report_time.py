"""Display source timestamps without changing transcript order or inventing dates."""
from datetime import datetime, timedelta, timezone
import math

REPORT_ZONE = timezone(timedelta(hours=8))


def parse_time(value):
    try:
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            if not math.isfinite(value):
                return None
            # Normalized clients provide Unix seconds or milliseconds.
            seconds = value / 1000 if abs(value) >= 100_000_000_000 else value
            return datetime.fromtimestamp(seconds, timezone.utc).astimezone(REPORT_ZONE)
        if isinstance(value, str):
            date = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return date.astimezone(REPORT_ZONE) if date.tzinfo else None
    except (ValueError, OverflowError, OSError):
        pass
    return None
