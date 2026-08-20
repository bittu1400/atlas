"""Port interface for publication and video export."""

from typing import Any, Protocol

from atlas.domain.media.models import RenderArtifact


class Publisher(Protocol):
    """Port for publishing approved video artifacts (Phase 1: manual export / stubbed)."""

    async def publish(
        self,
        artifact: RenderArtifact,
        channel_id: str,
        metadata: dict[str, Any],
    ) -> str:
        """Publish video to destination platform, returning publication ID."""
        ...
