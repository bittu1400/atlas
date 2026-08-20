"""Quota Governance and Rate-Limiter Token Buckets.

As specified in Invariant 8, SPEC §11, and ADR-0004:
- Quota is a first-class resource. Every model call is metered before invocation.
- Tracks per-minute and per-day windows for free-tier providers.
- Records metered calls to model_calls audit table and quota_ledger.
"""

from datetime import datetime, timedelta
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
    """Manages provider rate limits, token buckets, and quota ledger accounting."""

    def __init__(
        self,
        execution_repo: ExecutionRepositoryPort,
        provider_limits: dict[str, dict[str, int]] | None = None,
    ) -> None:
        self.execution_repo = execution_repo
        self.provider_limits = provider_limits or DEFAULT_PROVIDER_LIMITS
        # In-memory sliding window counters: {provider: [(timestamp, tokens)]}
        self._minute_calls: dict[str, list[datetime]] = {}
        self._daily_calls: dict[str, list[datetime]] = {}
        self._daily_tokens: dict[str, int] = {}
        self._daily_reset: dict[str, datetime] = {}

    def _get_limits(self, provider: str) -> dict[str, int]:
        return self.provider_limits.get(
            provider, self.provider_limits.get("fake", DEFAULT_PROVIDER_LIMITS["fake"])
        )

    def check_rate_limits(self, provider: str, estimated_tokens: int = 100) -> None:
        """Verify that provider rate limits allow an immediate model call."""
        now = utc_now()
        limits = self._get_limits(provider)

        # 1. Check minute window (RPM)
        minute_ago = now - timedelta(minutes=1)
        calls = self._minute_calls.setdefault(provider, [])
        # Prune old calls
        self._minute_calls[provider] = [t for t in calls if t > minute_ago]

        if len(self._minute_calls[provider]) >= limits["rpm"]:
            logger.warn(
                "quota.rate_limit_hit", provider=provider, count=len(self._minute_calls[provider])
            )
            raise RateLimitExceededError(provider)

        # 2. Check daily window (RPD and TPD)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        last_reset = self._daily_reset.get(provider, start_of_day)
        if last_reset < start_of_day:
            self._daily_calls[provider] = []
            self._daily_tokens[provider] = 0
            self._daily_reset[provider] = start_of_day

        daily_calls = self._daily_calls.setdefault(provider, [])
        if len(daily_calls) >= limits["rpd"]:
            logger.error("quota.daily_requests_exhausted", provider=provider)
            raise QuotaExceededError(provider, "daily requests")

        daily_tokens = self._daily_tokens.setdefault(provider, 0)
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

        # If not cached, update in-memory counters
        if not cached:
            self._minute_calls.setdefault(provider, []).append(now)
            self._daily_calls.setdefault(provider, []).append(now)
            self._daily_tokens[provider] = self._daily_tokens.get(provider, 0) + total_tokens

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
        if self.execution_repo:
            await self.execution_repo.record_model_call(model_call)

            # If not cached, record QuotaLedger entries for minute and day windows
            if not cached and total_tokens > 0:
                minute_start = now.replace(second=0, microsecond=0)
                day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

                # Minute ledger entry
                await self.execution_repo.record_quota_consumption(
                    QuotaLedgerEntry(
                        id=generate_id("qle"),
                        provider=provider,
                        window_type=WindowType.MINUTE,
                        window_start=minute_start,
                        tokens_consumed=total_tokens,
                        requests_consumed=1,
                        run_id=run_id if run_id != "run_unassigned" else None,
                        created_at=now,
                    )
                )

                # Day ledger entry
                await self.execution_repo.record_quota_consumption(
                    QuotaLedgerEntry(
                        id=generate_id("qle"),
                        provider=provider,
                        window_type=WindowType.DAY,
                        window_start=day_start,
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
