"""Integration tests for Claim Usages / Impact Index (ADR-0003).

When a Claim is retracted or refuted, the Impact Index answers exactly
which published renders and beats used it for corrections workflows.
"""

from datetime import UTC, datetime

import pytest
from atlas.adapters.persistence.repositories.source_repository import SourceRepository
from atlas.domain.knowledge.models import (
    AssertionType,
    Claim,
    ClaimStatus,
    ClaimUsage,
)
from atlas.platform.ids import generate_claim_id
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_claim_impact_index_records_and_retrieves_usages(
    db_session: AsyncSession,
) -> None:
    """Verify recording and querying Claim usages across published renders."""
    repo = SourceRepository(db_session)
    now = datetime(2026, 7, 30, 10, 0, 0, tzinfo=UTC)

    # 1. Create a Claim
    claim_id = generate_claim_id()
    claim = Claim(
        id=claim_id,
        text="Bengal tigers have unique stripe patterns akin to human fingerprints.",
        assertion_type=AssertionType.FACT,
        confidence=1.0,
        status=ClaimStatus.VERIFIED,
        created_at=now,
    )
    await repo.save_claim(claim)

    # 2. Record usages in two different renders
    usage1 = ClaimUsage(
        id="usg_01",
        claim_id=claim_id,
        render_id="rnd_tiger_origins_vertical",
        beat_id="beat_03_identification",
        used_at=datetime(2026, 7, 30, 14, 0, 0, tzinfo=UTC),
    )
    usage2 = ClaimUsage(
        id="usg_02",
        claim_id=claim_id,
        render_id="rnd_tiger_origins_horizontal",
        beat_id="beat_03_identification",
        used_at=datetime(2026, 7, 30, 14, 5, 0, tzinfo=UTC),
    )

    await repo.record_claim_usage(usage1)
    await repo.record_claim_usage(usage2)

    # 3. Query Impact Index for the Claim
    usages = await repo.get_usages_for_claim(claim_id)
    assert len(usages) == 2
    render_ids = {u.render_id for u in usages}
    assert "rnd_tiger_origins_vertical" in render_ids
    assert "rnd_tiger_origins_horizontal" in render_ids
    assert usages[0].used_at >= usages[1].used_at  # Sorted desc by usage time
