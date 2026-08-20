"""Time and clock utilities enforcing UTC internally and timezone-aware conversions.

As defined in ADR-0007 and SPEC §14, Atlas strictly distinguishes four clocks:
1. UTC Clock - all stored timestamps and internal calculations.
2. Operator Clock - Asia/Kathmandu (UTC+05:45, no DST) for dashboard display, approval reminders,
   and quiet hours. NEVER used for publishing calculations.
3. Audience Clock - per Channel (e.g. America/New_York) - the ONLY clock used for publish windows.
4. Provider Reset Clock - per provider quota day boundary.
"""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

# Operator timezone constant as fixed in ADR-0007
OPERATOR_TIMEZONE_NAME: str = "Asia/Kathmandu"
OPERATOR_TIMEZONE: ZoneInfo = ZoneInfo(OPERATOR_TIMEZONE_NAME)


def utc_now() -> datetime:
    """Return current timestamp in UTC with timezone attached.

    Ensures no timezone-naive datetime is ever created or stored in Atlas.
    """
    return datetime.now(UTC)


def to_utc(dt: datetime) -> datetime:
    """Convert any timezone-aware datetime to UTC."""
    if dt.tzinfo is None:
        raise ValueError("Cannot convert naive datetime to UTC; tzinfo required")
    return dt.astimezone(UTC)


def to_operator_time(utc_dt: datetime) -> datetime:
    """Convert UTC datetime to the operator's local timezone (Asia/Kathmandu).

    Used exclusively for dashboard UI, operator reminders, and quiet hours.
    """
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=UTC)
    return utc_dt.astimezone(OPERATOR_TIMEZONE)


def to_audience_time(utc_dt: datetime, audience_tz_name: str) -> datetime:
    """Convert UTC datetime to a Channel's audience timezone using IANA zone rules.

    Uses real tz database rules at calculation time to accurately handle DST.
    """
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=UTC)
    target_tz = ZoneInfo(audience_tz_name)
    return utc_dt.astimezone(target_tz)
