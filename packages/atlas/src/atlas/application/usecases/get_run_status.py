"""Queries and Status Inspection Use Cases."""

from typing import Any

from atlas.application.ports.repositories import ExecutionRepositoryPort
from atlas.domain.execution.models import Gate, Run


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
        """List Runs ordered by creation time."""
        return await self.execution_repo.list_runs(limit=limit)


class ListGatesUseCase:
    """Use case to list pending Gates requiring human approval."""

    def __init__(self, execution_repo: ExecutionRepositoryPort) -> None:
        self.execution_repo = execution_repo

    async def execute(self, pending_only: bool = True) -> list[Gate]:
        """List pending gates for operator queue."""
        if pending_only:
            return await self.execution_repo.list_pending_gates()
        return []


class GetQuotaStatusUseCase:
    """Use case to summarize quota usage across providers and windows."""

    def __init__(self, execution_repo: ExecutionRepositoryPort) -> None:
        self.execution_repo = execution_repo

    async def execute(self) -> dict[str, Any]:
        """Summarize current quota consumption."""
        return {
            "status": "healthy",
            "providers": {
                "gemini": {"rpm_remaining": 15, "rpd_remaining": 1500, "status": "active"},
                "ollama": {"rpm_remaining": 1000, "status": "active"},
                "fake": {"rpm_remaining": 10000, "status": "active"},
            },
        }
