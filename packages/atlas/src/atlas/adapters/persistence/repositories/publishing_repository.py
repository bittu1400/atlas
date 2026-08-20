"""Repository for Channels, Publishing Windows, and Blackout Rules (ADR-0007)."""

from atlas.adapters.persistence.tables import (
    BlackoutRuleTable,
    ChannelTable,
    PublishingWindowTable,
)
from atlas.domain.publishing.models import (
    BlackoutRule,
    Channel,
    PublishingWindow,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class PublishingRepository:
    """Data access repository for Channels, Publishing Windows, and Blackout constraints."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # =========================================================================
    # Channels
    # =========================================================================

    async def save_channel(self, channel: Channel) -> Channel:
        """Persist or update a Channel."""
        existing = await self.session.get(ChannelTable, channel.id)
        if existing:
            existing.name = channel.name
            existing.audience_timezone = channel.audience_timezone
            existing.style_profile = channel.style_profile
        else:
            row = ChannelTable(
                id=channel.id,
                name=channel.name,
                audience_timezone=channel.audience_timezone,
                style_profile=channel.style_profile,
                created_at=channel.created_at,
            )
            self.session.add(row)
        await self.session.flush()
        return channel

    async def get_channel(self, channel_id: str) -> Channel | None:
        """Fetch Channel by ID."""
        row = await self.session.get(ChannelTable, channel_id)
        if not row:
            return None
        return Channel(
            id=row.id,
            name=row.name,
            audience_timezone=row.audience_timezone,
            style_profile=dict(row.style_profile),
            created_at=row.created_at,
        )

    # =========================================================================
    # Publishing Windows (Priors & Learned Windows)
    # =========================================================================

    async def save_window(self, window: PublishingWindow) -> PublishingWindow:
        """Persist a Publishing Window."""
        row = PublishingWindowTable(
            id=window.id,
            channel_id=window.channel_id,
            platform=window.platform,
            format=window.format,
            day_of_week=window.day_of_week,
            local_start_time=window.local_start_time,
            local_end_time=window.local_end_time,
            rank=window.rank,
            source=window.source,
            confidence=window.confidence,
        )
        self.session.add(row)
        await self.session.flush()
        return window

    async def get_windows(
        self,
        channel_id: str,
        platform: str | None = None,
        format: str | None = None,
        day_of_week: int | None = None,
    ) -> list[PublishingWindow]:
        """Fetch matching Publishing Windows ordered by rank ascending."""
        stmt = select(PublishingWindowTable).where(PublishingWindowTable.channel_id == channel_id)
        if platform:
            stmt = stmt.where(PublishingWindowTable.platform == platform)
        if format:
            stmt = stmt.where(PublishingWindowTable.format == format)
        if day_of_week is not None:
            stmt = stmt.where(PublishingWindowTable.day_of_week == day_of_week)

        stmt = stmt.order_by(PublishingWindowTable.rank.asc())
        result = await self.session.execute(stmt)
        return [
            PublishingWindow(
                id=r.id,
                channel_id=r.channel_id,
                platform=r.platform,
                format=r.format,
                day_of_week=r.day_of_week,
                local_start_time=r.local_start_time,
                local_end_time=r.local_end_time,
                rank=r.rank,
                source=r.source,
                confidence=r.confidence,
            )
            for r in result.scalars().all()
        ]

    # =========================================================================
    # Blackout Rules
    # =========================================================================

    async def save_blackout_rule(self, rule: BlackoutRule) -> BlackoutRule:
        """Persist a Blackout Rule."""
        existing = await self.session.get(BlackoutRuleTable, rule.id)
        if existing:
            existing.local_start_time = rule.local_start_time
            existing.local_end_time = rule.local_end_time
            existing.is_enforced = rule.is_enforced
        else:
            row = BlackoutRuleTable(
                id=rule.id,
                local_start_time=rule.local_start_time,
                local_end_time=rule.local_end_time,
                is_enforced=rule.is_enforced,
            )
            self.session.add(row)
        await self.session.flush()
        return rule

    async def get_active_blackout_rules(self) -> list[BlackoutRule]:
        """Fetch all active blackout constraints."""
        stmt = select(BlackoutRuleTable).where(BlackoutRuleTable.is_enforced == True)  # noqa: E712
        result = await self.session.execute(stmt)
        return [
            BlackoutRule(
                id=r.id,
                local_start_time=r.local_start_time,
                local_end_time=r.local_end_time,
                is_enforced=r.is_enforced,
            )
            for r in result.scalars().all()
        ]
