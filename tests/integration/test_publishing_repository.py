"""Integration tests for Channels, Publishing Windows, and Blackout Rules (ADR-0007)."""

from datetime import UTC, datetime, time

import pytest
from atlas.adapters.persistence.repositories.publishing_repository import PublishingRepository
from atlas.domain.publishing.models import (
    BlackoutRule,
    Channel,
    PublishingWindow,
)
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_channel_and_publishing_windows_lifecycle(
    db_session: AsyncSession,
) -> None:
    """Test Channel creation, publishing window priors, and blackout rule enforcement."""
    repo = PublishingRepository(db_session)
    now = datetime(2026, 7, 30, 10, 0, 0, tzinfo=UTC)

    # 1. Create Channel
    channel = Channel(
        id="origins",
        name="ORIGINS",
        audience_timezone="America/New_York",
        style_profile={"theme": "archival"},
        created_at=now,
    )
    await repo.save_channel(channel)

    retrieved_channel = await repo.get_channel("origins")
    assert retrieved_channel is not None
    assert retrieved_channel.name == "ORIGINS"
    assert retrieved_channel.audience_timezone == "America/New_York"

    # 2. Save Seeded Publishing Windows (ADR-0007 §2)
    # YouTube long-form: Sunday 09:00 - 11:00
    win_yt = PublishingWindow(
        id="win_yt_sun",
        channel_id="origins",
        platform="youtube",
        content_format="horizontal_long",
        day_of_week=6,  # Sunday
        local_start_time=time(9, 0),
        local_end_time=time(11, 0),
        rank=1,
        source="Seed Research - Benchmark Study 2026",
        confidence=0.85,
    )
    # TikTok short vertical: Tue 09:00 - 12:00
    win_tt = PublishingWindow(
        id="win_tt_tue",
        channel_id="origins",
        platform="tiktok",
        content_format="vertical_60s",
        day_of_week=1,  # Tuesday
        local_start_time=time(9, 0),
        local_end_time=time(12, 0),
        rank=1,
        source="Seed Research - Short Form Priors",
        confidence=0.75,
    )
    await repo.save_window(win_yt)
    await repo.save_window(win_tt)

    # 3. Query Windows by Platform and Format
    tt_windows = await repo.get_windows(
        channel_id="origins", platform="tiktok", content_format="vertical_60s"
    )
    assert len(tt_windows) == 1
    assert tt_windows[0].local_start_time == time(9, 0)
    assert tt_windows[0].confidence == 0.75

    # 4. Save and Query Blackout Rules
    rule = BlackoutRule(
        id="blk_std",
        earliest_allowed_time=time(6, 0),
        latest_allowed_time=time(22, 0),
        is_enforced=True,
    )
    await repo.save_blackout_rule(rule)

    active_rules = await repo.get_active_blackout_rules()
    assert len(active_rules) >= 1
    assert any(
        r.earliest_allowed_time == time(6, 0) and r.latest_allowed_time == time(22, 0)
        for r in active_rules
    )
