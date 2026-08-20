"""Domain models for Publishing Schedule, Time Zones, and Windows.

As specified in ADR-0007 and SPEC §14:
- Audience timezone is a property of the Channel (never inherited from the operator).
- Publishing windows are data (priors) carrying confidence and source attribution.
- Blackout window (22:00 to 06:00 audience-local) is an enforced hard constraint.
- Time arithmetic uses IANA tz database at calculation time.
"""

import zoneinfo
from datetime import datetime, time
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SchedulingStrategy(StrEnum):
    """Publish scheduling strategy."""

    AUDIENCE_LOCAL = "audience_local"  # Target highest-ranked audience window (default)
    GLOBAL_UTC_PEAK = "global_utc_peak"  # Target 10:00 / 14:00 / 21:00 UTC peaks


class Channel(BaseModel):
    """Publishing identity carrying a Style Profile and Audience Timezone."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Unique Channel ID (e.g. origins)")
    name: str = Field(description="Display name")
    audience_timezone: str = Field(
        default="America/New_York",
        description="IANA timezone identifier for Channel's primary audience",
    )
    style_profile: dict[str, Any] = Field(
        default_factory=dict, description="Style Profile crafting parameters"
    )
    created_at: datetime = Field(description="Creation timestamp in UTC")

    @field_validator("audience_timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        if v not in zoneinfo.available_timezones():
            raise ValueError(f"Invalid timezone: {v}")
        return v


class PublishingWindow(BaseModel):
    """Seeded or learned window in audience-local time."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Unique Publishing Window ID")
    channel_id: str = Field(description="Associated Channel ID")
    platform: str = Field(description="Platform name (youtube, tiktok, instagram, etc.)")
    content_format: str = Field(description="Content format (e.g. vertical_60s, horizontal_long)")
    day_of_week: int = Field(ge=0, le=6, description="Day of week: 0=Monday, 6=Sunday")
    local_start_time: time = Field(description="Window start time in audience-local clock")
    local_end_time: time = Field(description="Window end time in audience-local clock")
    rank: int = Field(default=1, description="Rank within platform (1=highest engagement)")
    source: str = Field(description="Provenance source of this window (e.g. Seed Research)")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence in window")


class BlackoutRule(BaseModel):
    """Enforced blackout rule prohibiting publishing in sleeping hours."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Unique rule ID")
    earliest_allowed_time: time = Field(
        default=time(6, 0), description="Earliest allowable publish time (06:00)"
    )
    latest_allowed_time: time = Field(
        default=time(22, 0), description="Latest allowable publish time (22:00)"
    )
    is_enforced: bool = Field(default=True, description="Whether constraint is active")


class PublishSlot(BaseModel):
    """Concrete UTC instant allocated for publishing."""

    model_config = ConfigDict(frozen=True)

    utc_scheduled_time: datetime = Field(description="Publish instant in UTC")
    channel_id: str = Field(description="Target Channel ID")
    platform: str = Field(description="Platform name")
    content_format: str = Field(description="Content format")
    strategy: SchedulingStrategy = Field(default=SchedulingStrategy.AUDIENCE_LOCAL)
