"""Domain models for Media, Scenes, Storyboards, Sound, and Renders.

As specified in SPEC §4, §6, and ADR-0005:
- Dual aspect ratios: 9:16 (vertical, 1080x1920) and 16:9 (horizontal, 1920x1080).
- Scenes pair narrative Beats to archival visual assets and motion treatments.
- RenderArtifacts track generated MP4 blobs, WebVTT captions, and provenance.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RenderTarget(StrEnum):
    """Supported render aspect ratios and layout targets."""

    VERTICAL = "vertical"  # 9:16 (1080x1920) for Shorts / TikTok
    HORIZONTAL = "horizontal"  # 16:9 (1920x1080) for traditional YouTube


class MotionTreatment(StrEnum):
    """Visual motion treatment for archival stills."""

    SLOW_ZOOM_IN = "slow_zoom_in"
    SLOW_ZOOM_OUT = "slow_zoom_out"
    PAN_LEFT = "pan_left"
    PAN_RIGHT = "pan_right"
    STATIC = "static"


class Scene(BaseModel):
    """One visual scene pairing a narrative Beat with an archival Asset."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Unique Scene ID")
    scene_index: int = Field(ge=1, description="Sequential scene index (1-indexed)")
    beat_id: str = Field(description="Associated narrative Beat ID")
    asset_id: str = Field(description="Selected archival Asset ID")
    motion_treatment: MotionTreatment = Field(
        default=MotionTreatment.SLOW_ZOOM_IN, description="Visual motion applied to still asset"
    )
    focal_crop: dict[str, float] = Field(
        default_factory=lambda: {"x": 0.5, "y": 0.5},
        description="Focal point coordinate for responsive 9:16 / 16:9 cropping",
    )
    start_time_seconds: float = Field(ge=0.0, description="Scene start timestamp in seconds")
    duration_seconds: float = Field(gt=0.0, description="Scene duration in seconds")


class Storyboard(BaseModel):
    """Complete storyboard mapping narrative beats to visual scenes."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Unique Storyboard ID")
    script_id: str = Field(description="Associated Script ID")
    timing_plan_id: str = Field(description="Associated Timing Plan ID")
    scenes: list[Scene] = Field(min_length=1, description="Ordered list of visual scenes")
    render_targets: list[RenderTarget] = Field(
        default_factory=lambda: [RenderTarget.VERTICAL, RenderTarget.HORIZONTAL],
        description="Target render formats",
    )
    created_at: datetime = Field(description="Creation timestamp in UTC")


class SfxCue(BaseModel):
    """Individual sound effect cue aligned to timeline."""

    model_config = ConfigDict(frozen=True)

    sfx_id: str = Field(description="Sound effect identifier / asset ID")
    timestamp_seconds: float = Field(ge=0.0, description="Trigger timestamp in seconds")
    volume: float = Field(ge=0.0, le=1.0, default=0.8, description="Relative volume level")
    cue_type: str = Field(
        default="keystroke", description="Cue type (keystroke, transition, ambient)"
    )


class SoundTrack(BaseModel):
    """Complete audio composition plan."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Unique SoundTrack ID")
    storyboard_id: str = Field(description="Associated Storyboard ID")
    music_bed_asset_id: str = Field(description="Background music asset ID")
    music_volume: float = Field(ge=0.0, le=1.0, default=0.25, description="Music bed ducking level")
    sfx_cues: list[SfxCue] = Field(default_factory=list, description="Ordered list of SFX cues")
    target_lufs: float = Field(
        default=-14.0, description="Integrated loudness target in LUFS (±1.0 LUFS)"
    )
    created_at: datetime = Field(description="Creation timestamp in UTC")


class RenderArtifact(BaseModel):
    """Rendered video output artifact."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Unique Render Artifact ID")
    run_id: str = Field(description="Associated Run ID")
    storyboard_id: str = Field(description="Associated Storyboard ID")
    render_target: RenderTarget = Field(description="Render target format")
    video_storage_key: str = Field(description="Content-addressed storage key for the MP4 video")
    captions_storage_key: str = Field(
        description="Content-addressed storage key for WebVTT captions"
    )
    duration_seconds: float = Field(gt=0.0, description="Final video duration in seconds")
    file_size_bytes: int = Field(ge=0, description="File size in bytes")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Render metadata and parameters"
    )
    created_at: datetime = Field(description="Creation timestamp in UTC")
