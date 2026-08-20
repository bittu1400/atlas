"""Port interface for Video Rendering (Remotion / Chromium)."""

from typing import Protocol

from atlas.domain.media.models import RenderArtifact, RenderTarget, Storyboard
from atlas.domain.script.models import TimingPlan


class Renderer(Protocol):
    """Port for rendering compositions into MP4 video and WebVTT captions."""

    async def render(
        self,
        storyboard: Storyboard,
        timing_plan: TimingPlan,
        target: RenderTarget,
        run_id: str,
    ) -> RenderArtifact:
        """Render a single aspect ratio target from storyboard and timing plan."""
        ...
