"""YouTube publishing adapter."""

from typing import Any

from atlas.application.ports.publish import Publisher
from atlas.domain.media.models import RenderArtifact


class YouTubePublisher(Publisher):
    """Stubbed publisher for YouTube that mocks the API."""

    async def publish(
        self,
        artifact: RenderArtifact,
        channel_id: str,
        metadata: dict[str, Any],
    ) -> str:
        print(f"Simulating YouTube API call for channel '{channel_id}'...")
        print(f"Payload metadata: {metadata}")
        print(f"Artifact URI: {artifact.uri}")
        return "yt_mock_video_id_123"
