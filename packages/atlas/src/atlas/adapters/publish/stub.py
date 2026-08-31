"""Stub publisher.

Rule R3: this stub does not wear the name of the thing it is standing in for.
It performs no network call and mints no real external ID; a real YouTube
adapter (OAuth2, resumable upload) does not exist yet, and `docs/STATUS.md`
says so. Its returned ID is deliberately marked `stub:` so a caller that treats
it as a live video ID is obvious in the data.
"""

from typing import Any

from atlas.application.ports.publish import Publisher
from atlas.domain.media.models import RenderArtifact
from atlas.platform.logging import get_logger

logger = get_logger("adapters.publish.stub")


class StubPublisher(Publisher):
    """Records what would have been published and returns a clearly marked stub ID."""

    async def publish(
        self,
        artifact: RenderArtifact,
        channel_id: str,
        metadata: dict[str, Any],
    ) -> str:
        """Log the intended publication and return a stub external ID."""
        logger.info(
            "publish.stub_invoked",
            channel_id=channel_id,
            artifact_id=artifact.id,
            render_target=artifact.render_target.value,
            video_storage_key=artifact.video_storage_key,
            duration_seconds=artifact.duration_seconds,
            metadata_keys=sorted(metadata),
        )
        return f"stub:{artifact.id}"
