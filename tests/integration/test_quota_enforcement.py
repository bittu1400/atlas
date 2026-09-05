"""Invariant 8: the quota budget is shared, and every model call is metered.

`QuotaManager` used to count calls in process memory and never read the
`quota_ledger` rows it wrote, while its own docstring called that ledger "the
canonical distributed source of truth". Atlas runs one process per CLI
invocation and one per worker, so every process started with a full daily
budget — on a free tier that allows twenty requests a day, that is the same as
having no limit (defect V-04). These tests assert the ledger is read back.
"""

import pytest
from atlas.adapters.persistence.repositories.execution_repository import ExecutionRepository
from atlas.platform.errors import QuotaExceededError, RateLimitExceededError
from atlas.platform.quota import QuotaManager
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

TIGHT_LIMITS = {"gemini": {"rpm": 2, "rpd": 3, "tpm": 1000, "tpd": 10_000}}


async def _spend_one(manager: QuotaManager, tokens: int = 10) -> None:
    await manager.record_invocation(
        provider="gemini",
        model_id="gemini-2.0-flash",
        prompt_version="v1",
        parameters={},
        code_version="v1",
        input_tokens=tokens,
        output_tokens=0,
        latency_ms=1,
    )


@pytest.mark.asyncio
async def test_rate_limit_counts_calls_recorded_by_another_manager(
    db_session: AsyncSession,
) -> None:
    """A second QuotaManager — a second process — inherits the spent budget."""
    repo = ExecutionRepository(db_session)
    worker_one = QuotaManager(repo, provider_limits=TIGHT_LIMITS)

    await worker_one.check_rate_limits("gemini")
    await _spend_one(worker_one)
    await worker_one.check_rate_limits("gemini")
    await _spend_one(worker_one)

    # A freshly constructed manager holds no in-memory history at all.
    worker_two = QuotaManager(repo, provider_limits=TIGHT_LIMITS)
    with pytest.raises(RateLimitExceededError) as exc_info:
        await worker_two.check_rate_limits("gemini")
    assert exc_info.value.provider == "gemini"


@pytest.mark.asyncio
async def test_daily_request_budget_is_enforced_from_the_ledger(
    db_session: AsyncSession,
) -> None:
    """RPD is spent across managers, not reset by one."""
    repo = ExecutionRepository(db_session)
    limits = {"gemini": {"rpm": 100, "rpd": 3, "tpm": 10_000, "tpd": 100_000}}

    for _ in range(3):
        manager = QuotaManager(repo, provider_limits=limits)
        await manager.check_rate_limits("gemini")
        await _spend_one(manager)

    with pytest.raises(QuotaExceededError):
        await QuotaManager(repo, provider_limits=limits).check_rate_limits("gemini")


@pytest.mark.asyncio
async def test_a_zero_token_call_still_costs_a_request(db_session: AsyncSession) -> None:
    """A provider that reports no tokens still consumed one of the day's requests.

    The ledger write used to be gated on `total_tokens > 0`, so such a call was
    metered nowhere and the free tier drained invisibly.
    """
    repo = ExecutionRepository(db_session)
    manager = QuotaManager(repo, provider_limits=TIGHT_LIMITS)

    await _spend_one(manager, tokens=0)

    result = await db_session.execute(
        text(
            "SELECT COALESCE(SUM(requests_consumed), 0) FROM quota_ledger "
            "WHERE provider = 'gemini' AND window_type = 'day'"
        )
    )
    assert result.scalar_one() == 1


@pytest.mark.asyncio
async def test_a_cached_response_costs_no_request(db_session: AsyncSession) -> None:
    """A cache hit is audited as a model call but consumes no quota."""
    repo = ExecutionRepository(db_session)
    manager = QuotaManager(repo, provider_limits=TIGHT_LIMITS)

    await manager.record_invocation(
        provider="gemini",
        model_id="gemini-2.0-flash",
        prompt_version="v1",
        parameters={},
        code_version="v1",
        input_tokens=10,
        output_tokens=10,
        latency_ms=1,
        cached=True,
    )

    ledger = await db_session.execute(
        text("SELECT COUNT(*) FROM quota_ledger WHERE provider = 'gemini'")
    )
    calls = await db_session.execute(
        text("SELECT COUNT(*) FROM model_calls WHERE provider = 'gemini'")
    )
    assert ledger.scalar_one() == 0
    assert calls.scalar_one() == 1
