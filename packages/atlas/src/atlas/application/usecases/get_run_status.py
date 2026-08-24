"""Queries and Status Inspection Use Cases."""

from typing import Any

from atlas.application.ports.repositories import ExecutionRepositoryPort
from atlas.domain.execution.models import Gate, Run
from atlas.platform.quota import DEFAULT_PROVIDER_LIMITS


class GetRunStatusUseCase:
    """Use case to inspect full status of a Run including steps and gates."""

    def __init__(self, execution_repo: ExecutionRepositoryPort) -> None:
        self.execution_repo = execution_repo

    async def execute(self, run_id: str) -> Run:
        """Fetch Run details."""
        return await self.execution_repo.get_run(run_id)


class ListRunsUseCase:
    """Use case to list existing pipeline Runs."""

    def __init__(self, execution_repo: ExecutionRepositoryPort) -> None:
        self.execution_repo = execution_repo

    async def execute(self, limit: int = 50) -> list[Run]:
        """List Runs ordered by creation time with bounded limit."""
        clamped_limit = min(max(limit, 1), 200)
        return await self.execution_repo.list_runs(limit=clamped_limit)


class ListGatesUseCase:
    """Use case to list pending or all Gates for operator inspection."""

    def __init__(self, execution_repo: ExecutionRepositoryPort) -> None:
        self.execution_repo = execution_repo

    async def execute(self, pending_only: bool = True) -> list[Gate]:
        """List pending gates for operator queue or all gates for history."""
        if pending_only:
            return await self.execution_repo.list_pending_gates()
        return await self.execution_repo.list_all_gates()


class GetQuotaStatusUseCase:
    """Use case to summarize quota usage across providers and windows."""

    def __init__(self, execution_repo: ExecutionRepositoryPort) -> None:
        self.execution_repo = execution_repo

    async def execute(self) -> dict[str, Any]:
        """Summarize current quota allocation and consumed metrics from ledger."""
        consumed = await self.execution_repo.get_quota_consumption_summary()
        provider_status: dict[str, Any] = {}

        for provider, limits in DEFAULT_PROVIDER_LIMITS.items():
            prov_consumed = consumed.get(provider, {})
            rpm_limit = limits.get("rpm", 1000)
            rpd_limit = limits.get("rpd", 100000)

            minute_requests = prov_consumed.get("minute_requests", 0)
            daily_requests = prov_consumed.get("daily_requests", 0)

            rpm_remaining = max(0, rpm_limit - minute_requests)
            rpd_remaining = max(0, rpd_limit - daily_requests)

            provider_status[provider] = {
                "rpm_remaining": rpm_remaining,
                "rpd_remaining": rpd_remaining,
                "status": "active" if rpm_remaining > 0 and rpd_remaining > 0 else "throttled",
            }

        return {
            "status": "healthy",
            "providers": provider_status,
        }
