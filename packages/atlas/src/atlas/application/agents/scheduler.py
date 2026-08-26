"""Publish scheduler."""

import zoneinfo
from datetime import datetime

from atlas.domain.publishing.models import (
    BlackoutRule,
    Channel,
    PublishSlot,
    SchedulingStrategy,
)


class PublishScheduler:
    """Agent responsible for scheduling publish slots."""

    def __init__(self, blackout_rule: BlackoutRule | None = None):
        if blackout_rule is None:
            self.blackout_rule = BlackoutRule(id="default_blackout")
        else:
            self.blackout_rule = blackout_rule

    def schedule(
        self,
        channel: Channel,
        platform: str,
        content_format: str,
        proposed_local_datetime: datetime,
    ) -> PublishSlot:
        """
        Schedule a publish slot enforcing blackout rules.
        
        Args:
            channel: The channel for publishing.
            platform: Platform name.
            content_format: Format of content.
            proposed_local_datetime: Proposed datetime in the audience timezone.
                If it has no tzinfo, it will be assumed to be in audience timezone.
                
        Returns:
            PublishSlot in UTC.
            
        Raises:
            BlackoutWindowViolationError if the local time falls in blackout window.
        """
        tz = zoneinfo.ZoneInfo(channel.audience_timezone)

        # Ensure it's localized
        if proposed_local_datetime.tzinfo is None:
            local_dt = proposed_local_datetime.replace(tzinfo=tz)
        else:
            local_dt = proposed_local_datetime.astimezone(tz)

        # Check blackout
        self.blackout_rule.validate_time(local_dt.time())

        # Convert to UTC
        utc_dt = local_dt.astimezone(zoneinfo.ZoneInfo("UTC"))

        return PublishSlot(
            utc_scheduled_time=utc_dt,
            channel_id=channel.id,
            platform=platform,
            content_format=content_format,
            strategy=SchedulingStrategy.AUDIENCE_LOCAL,
        )
