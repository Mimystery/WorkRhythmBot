from datetime import datetime, timedelta, timezone


def format_duration(td: timedelta) -> str:
    total_seconds = int(td.total_seconds())
    if total_seconds < 0:
        return "0m"
    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def format_time(dt: datetime) -> str:
    """Format datetime as HH:MM (UTC+0). Adjust offset here if needed."""
    return dt.strftime("%H:%M")
