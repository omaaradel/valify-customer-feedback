from datetime import datetime, timezone, timedelta
from typing import Optional


def get_since_date(
    mode: str,
    first_tx: datetime,
    days: Optional[int] = None,
) -> datetime:
    """Return the earliest UTC datetime to fetch feedback from.

    historical: go back to first_tx, but no more than 12 months.
    daily:      go back 48 hours (overlap window prevents gaps on failed runs).
    days:       explicit override. When provided, ignores mode and returns
                now - days. Useful for initial per-client sweeps (e.g. 30 days).
    """
    if days is not None:
        return datetime.now(timezone.utc) - timedelta(days=days)
    if mode == "historical":
        twelve_months_ago = datetime.now(timezone.utc) - timedelta(days=365)
        return max(first_tx, twelve_months_ago)
    return datetime.now(timezone.utc) - timedelta(hours=48)


def ensure_utc(dt: datetime) -> datetime:
    """Return dt as a UTC-aware datetime.

    google-play-scraper returns naive datetimes parsed from Unix timestamps
    using datetime.fromtimestamp(), which is local system time. On a UTC
    server this is correct. On a local machine (e.g. Cairo, UTC+2/+3) the
    naive datetime is 2-3 hours ahead of UTC, but for historical sweeps this
    offset is immaterial. The dedup hash catches any re-fetched duplicates.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
