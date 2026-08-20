"""Unit tests for Timezone conversions and the 4 clocks from ADR-0007."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from atlas.platform.clock import (
    to_audience_time,
    to_operator_time,
    to_utc,
    utc_now,
)


def test_utc_now_has_utc_tzinfo() -> None:
    """utc_now() must always return timezone-aware UTC datetime."""
    now = utc_now()
    assert now.tzinfo == UTC


def test_to_operator_time_converts_to_kathmandu() -> None:
    """UTC converts correctly to Asia/Kathmandu (UTC+05:45)."""
    # 14:00 UTC -> 19:45 Kathmandu
    dt_utc = datetime(2026, 7, 30, 14, 0, 0, tzinfo=UTC)
    op_time = to_operator_time(dt_utc)
    assert op_time.hour == 19
    assert op_time.minute == 45
    assert op_time.tzinfo is not None
    assert str(op_time.tzinfo) == "Asia/Kathmandu"


def test_to_audience_time_converts_with_dst() -> None:
    """Audience time conversion respects IANA rules and Daylight Saving Time."""
    # July 30 (EDT: UTC-4): 14:00 UTC -> 10:00 EDT
    dt_summer = datetime(2026, 7, 30, 14, 0, 0, tzinfo=UTC)
    aud_summer = to_audience_time(dt_summer, "America/New_York")
    assert aud_summer.hour == 10
    assert aud_summer.minute == 0

    # Dec 30 (EST: UTC-5): 14:00 UTC -> 09:00 EST
    dt_winter = datetime(2026, 12, 30, 14, 0, 0, tzinfo=UTC)
    aud_winter = to_audience_time(dt_winter, "America/New_York")
    assert aud_winter.hour == 9
    assert aud_winter.minute == 0


def test_to_utc_roundtrip() -> None:
    """Converting to audience and back to UTC preserves exact instant."""
    original_utc = datetime(2026, 7, 30, 14, 0, 0, tzinfo=UTC)
    aud_time = to_audience_time(original_utc, "Europe/London")
    restored_utc = to_utc(aud_time)
    assert original_utc == restored_utc


def test_dst_fall_back_ambiguity() -> None:
    """Nov 1, 2026, 1:30 AM is ambiguous in NY (EDT -> EST). fold=1 represents EST."""
    dt = datetime(2026, 11, 1, 1, 30, fold=1, tzinfo=ZoneInfo("America/New_York"))
    assert isinstance(dt.tzinfo, ZoneInfo)
    assert dt.tzinfo.key == "America/New_York"
    utc_dt = dt.astimezone(UTC)
    assert utc_dt.hour == 6  # 1:30 AM EST (UTC-5) -> 6:30 AM UTC


def test_dst_spring_forward_gap() -> None:
    """Mar 8, 2026, 2:30 AM does not exist in NY (spring-forward gap)."""
    # ZoneInfo handles non-existent times by standard disambiguation
    dt = datetime(2026, 3, 8, 2, 30, tzinfo=ZoneInfo("America/New_York"))
    assert isinstance(dt.tzinfo, ZoneInfo)


def test_naive_datetime_rejected() -> None:
    """Naive datetimes must be rejected by to_utc, to_operator_time, and to_audience_time."""
    import pytest

    naive_dt = datetime(2026, 7, 30, 14, 0, 0)
    with pytest.raises(ValueError, match="Cannot convert naive datetime"):
        to_utc(naive_dt)

    with pytest.raises(ValueError, match="Cannot convert naive datetime"):
        to_operator_time(naive_dt)

    with pytest.raises(ValueError, match="Cannot convert naive datetime"):
        to_audience_time(naive_dt, "America/New_York")
