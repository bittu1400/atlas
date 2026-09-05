"""Create Channel Use Case.

Defect V-15: `PublishingRepositoryPort.save_channel` had no production caller,
so the Channel a Run publishes to could only be created by a test fixture.
"""

from typing import Any

from atlas.application.ports.repositories import PublishingRepositoryPort
from atlas.domain.publishing.models import Channel
from atlas.platform.clock import utc_now
from atlas.platform.logging import get_logger

logger = get_logger("usecases.create_channel")


class CreateChannelUseCase:
    """Use case to register a publishing Channel."""

    def __init__(self, publishing_repo: PublishingRepositoryPort) -> None:
        self.publishing_repo = publishing_repo

    async def execute(
        self,
        channel_id: str,
        name: str,
        audience_timezone: str = "America/New_York",
        style_profile: dict[str, Any] | None = None,
    ) -> Channel:
        """Register a Channel with its audience clock and Style Profile."""
        channel = Channel(
            id=channel_id,
            name=name,
            audience_timezone=audience_timezone,
            style_profile=style_profile or {},
            created_at=utc_now(),
        )
        saved = await self.publishing_repo.save_channel(channel)
        logger.info("channel.created", channel_id=saved.id, audience_timezone=audience_timezone)
        return saved
