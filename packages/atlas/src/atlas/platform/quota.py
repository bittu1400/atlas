"""Quota Governance and Rate Limiting.

As specified in Invariant 8, SPEC §11, and ADR-0004:
- Quota is a first-class resource. Every model call is metered before invocation.
- Tracks per-minute and per-day windows for free-tier providers.
- Records metered calls to model_calls audit table and quota_ledger.

The windows are computed from `quota_ledger` on every check, never from process
memory. Atlas runs one process per CLI invocation and one per worker; an
in-memory counter hands each of them a fresh daily budget, which on a 20
requests/day tier is the same as having no limit at all (defect V-04).
"""

from typing import Any

from atlas.application.ports.repositories import ExecutionRepositoryPort
from atlas.domain.execution.models import ModelCall, QuotaLedgerEntry, WindowType
from atlas.platform.clock import utc_now
from atlas.platform.errors import QuotaExceededError, RateLimitExceededError
from atlas.platform.ids import generate_id
from atlas.platform.logging import get_logger

logger = get_logger("platform.quota")

# Default free-tier limits per provider
DEFAULT_PROVIDER_LIMITS: dict[str, dict[str, int]] = {
    "gemini": {
        "rpm": 15,
        "rpd": 1500,
        "tpm": 1_000_000,
        "tpd": 100_000_000,
    },
    "ollama": {
        "rpm": 1000,  # Local hardware constraint managed via GPU semaphore
        "rpd": 100_000,
        "tpm": 10_000_000,
        "tpd": 100_000_000,
    },
    "fake": {
        "rpm": 10_000,
        "rpd": 100_000,
        "tpm": 100_000_000,
        "tpd": 100_000_000,
    },
}


class QuotaManager:
    """Manages provider rate limits and quota ledger accounting.

    `quota_ledger` is the single source of truth for consumption: every check
    reads it, so two workers and a CLI invocation share one budget.
    """

    def __init__(
        self,
        execution_repo: ExecutionRepositoryPort,
        provider_limits: dict[str, dict[str, int]] | None = None,
    ) -> None:
        self.execution_repo = execution_repo
        self.provider_limits = provider_limits or DEFAULT_PROVIDER_LIMITS

    def _get_limits(self, provider: str) -> dict[str, int]:
        return self.provider_limits.get(
            provider, self.provider_limits.get("fake", DEFAULT_PROVIDER_LIMITS["fake"])
        )

    async def check_rate_limits(self, provider: str, estimated_tokens: int = 100) -> None:
        """Verify that provider rate limits allow an immediate model call.

        Reads the ledger rather than a process-local counter, so the limit holds
        across the API, the worker and every CLI invocation.
        """
        limits = self._get_limits(provider)
        consumed = (await self.execution_repo.get_quota_consumption_summary()).get(provider, {})

        minute_requests = consumed.get("minute_requests", 0)
        if minute_requests >= limits["rpm"]:
            logger.warning("quota.rate_limit_hit", provider=provider, count=minute_requests)
            raise RateLimitExceededError(provider)

        daily_requests = consumed.get("daily_requests", 0)
        if daily_requests >= limits["rpd"]:
            logger.error("quota.daily_requests_exhausted", provider=provider)
            raise QuotaExceededError(provider, "daily requests")

        daily_tokens = consumed.get("daily_tokens", 0)
        if daily_tokens + estimated_tokens > limits["tpd"]:
            logger.error("quota.daily_tokens_exhausted", provider=provider)
            raise QuotaExceededError(provider, "daily tokens")

    async def record_invocation(
        self,
        provider: str,
        model_id: str,
        prompt_version: str,
        parameters: dict[str, Any],
        code_version: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        cached: bool = False,
        outcome: str = "success",
        run_id: str = "run_unassigned",
        step_id: str | None = None,
    ) -> ModelCall:
        """Record a completed or cached model invocation into the audit log and quota ledger."""
        now = utc_now()
        total_tokens = input_tokens + output_tokens

        # Record ModelCall audit row
        model_call = ModelCall(
            id=generate_id("call"),
            run_id=run_id,
            step_id=step_id,
            provider=provider,
            model_id=model_id,
            prompt_version=prompt_version,
            parameters=parameters,
            code_version=code_version,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cached=cached,
            outcome=outcome,
            cost_usd=0.0,
            created_at=now,
        )
        await self.execution_repo.record_model_call(model_call)

        # A cached response costs no request; an uncached one costs a request even
        # when the provider reports no tokens, so requests are counted regardless.
        if not cached:
            now_windows = (
                (WindowType.MINUTE, now.replace(second=0, microsecond=0)),
                (WindowType.DAY, now.replace(hour=0, minute=0, second=0, microsecond=0)),
            )
            for window_type, window_start in now_windows:
                await self.execution_repo.record_quota_consumption(
                    QuotaLedgerEntry(
                        id=generate_id("qle"),
                        provider=provider,
                        window_type=window_type,
                        window_start=window_start,
                        tokens_consumed=total_tokens,
                        requests_consumed=1,
                        run_id=run_id if run_id != "run_unassigned" else None,
                        created_at=now,
                    )
                )

        logger.info(
            "quota.invocation_recorded",
            provider=provider,
            model=model_id,
            tokens=total_tokens,
            cached=cached,
            run_id=run_id,
        )
        return model_call
