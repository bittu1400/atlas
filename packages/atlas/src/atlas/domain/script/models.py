"""Domain models for Scripts, Beats, and Timing Plans.

As specified in SPEC §4, §6, and ADR-0006:
- Every Beat carries Claim IDs ensuring 100% traceability.
- TimingPlan is the canonical artifact driving text pacing, visual cuts, sound design, and frame-accurate captions.
- Silent reading comprehension budget (~2.0-2.5 words/sec).
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Beat(BaseModel):
    """An individual narrative beat within a script."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Unique Beat ID (e.g. beat_01)")
    beat_index: int = Field(ge=1, description="Sequential order within script (1-indexed)")
    text: str = Field(description="On-screen text displayed during this beat")
    claim_ids: list[str] = Field(
        min_length=1, description="Claim IDs supporting this beat (non-negotiable traceability)"
    )
    duration_seconds: float = Field(
        ge=0.5, le=10.0, default=3.5, description="Target dwell time in seconds"
    )
    visual_cue: str | None = Field(
        default=None, description="Visual recommendation for archival asset matching"
    )


class Script(BaseModel):
    """Complete video script consisting of ordered Beats."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Unique Script ID")
    topic_id: str = Field(description="Associated Topic ID")
    knowledge_object_id: str = Field(description="Knowledge Object ID from which this is derived")
    ko_version: int = Field(ge=1, description="Knowledge Object version number")
    story_angle: str = Field(description="Selected narrative angle")
    beats: list[Beat] = Field(min_length=1, description="Ordered list of narrative beats")
    target_duration_seconds: float = Field(
        default=60.0, description="Target total duration in seconds"
    )
    created_at: datetime = Field(description="Creation timestamp in UTC")

    @property
    def total_words(self) -> int:
        """Total word count across all beats."""
        return sum(len(b.text.split()) for b in self.beats)

    @property
    def total_duration(self) -> float:
        """Sum of beat durations."""
        return sum(b.duration_seconds for b in self.beats)


class BeatTiming(BaseModel):
    """Calculated start and end timings for an individual Beat."""

    model_config = ConfigDict(frozen=True)

    beat_id: str = Field(description="Associated Beat ID")
    start_time_seconds: float = Field(ge=0.0, description="Start offset in seconds")
    end_time_seconds: float = Field(ge=0.0, description="End offset in seconds")
    word_count: int = Field(ge=0, description="Word count for reading pace validation")
    reading_pace_wps: float = Field(ge=0.0, description="Calculated words per second")


class CaptionCue(BaseModel):
    """Frame-accurate caption cue for WebVTT export."""

    model_config = ConfigDict(frozen=True)

    start_seconds: float = Field(ge=0.0, description="Start timestamp in seconds")
    end_seconds: float = Field(ge=0.0, description="End timestamp in seconds")
    text: str = Field(description="Caption text line")


class TimingPlan(BaseModel):
    """Canonical timing plan governing pacing, cuts, captions, and sound."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Unique Timing Plan ID")
    script_id: str = Field(description="Associated Script ID")
    total_duration_seconds: float = Field(
        default=60.0, description="Total video runtime in seconds"
    )
    beat_timings: list[BeatTiming] = Field(
        min_length=1, description="Exact timeline allocations per beat"
    )
    caption_cues: list[CaptionCue] = Field(
        default_factory=list, description="Generated caption cues"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Pacing profile metadata")
    created_at: datetime = Field(description="Creation timestamp in UTC")
