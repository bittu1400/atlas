"""Domain models for Pipeline Execution, State Machine, Gates, and Durability.

As specified in ADR-0001:
- Postgres is the queue and state store; Atlas owns the state machine.
- Suspension is a database row; human approval holds no memory or process.
- Steps are idempotent via (run_id, step_name, input_hash) and checkpointed.
- Shared GPU semaphore via resource_locks with expiring TTL.
- Token buckets and quota ledger per provider.
"""

from datetime import datetime
from enum import StrEnum

from atlas.domain.focus.models import FocusSnapshot
from pydantic import BaseModel, ConfigDict, Field


class RunStatus(StrEnum):
    """Lifecycle state of a pipeline Run."""

    PENDING = "pending"
    RUNNING = "running"
    SUSPENDED = "suspended"  # Suspended at a human gate
    REWORKING = "reworking"  # Quality check failed; regenerating
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"


class StepStatus(StrEnum):
    """Execution status of an individual Step."""

    PENDING = "pending"
    RUNNING = "running"
    SUSPENDED = "suspended"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class GateType(StrEnum):
    """Policy mode of a Gate."""

    AUTOMATIC = "automatic"
    MANUAL = "manual"
    HYBRID = "hybrid"


class GateStatus(StrEnum):
    """Resolution status of a Gate."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalDecision(StrEnum):
    """Human decision on a Gate."""

    APPROVED = "approved"
    REJECTED = "rejected"


class RejectionAction(StrEnum):
    """Action route resulting from a rejection."""

    REGENERATE = "regenerate"  # Re-run with feedback attached
    BRANCH = "branch"  # Try alternative story angle
    ABANDON = "abandon"  # Abandon run with recorded reason


class RejectionFeedback(BaseModel):
    """Structured, actionable critique attached to a rejection (SPEC §7)."""

    model_config = ConfigDict(frozen=True)

    target_ref: str = Field(description="Target identifier (e.g. Beat ID, Asset ID)")
    rubric_dimension: str = Field(description="Rubric dimension failed")
    reason: str = Field(description="Actionable explanation of the defect")
    action: RejectionAction = Field(
        default=RejectionAction.REGENERATE, description="Next route for the pipeline"
    )


class Run(BaseModel):
    """One execution of the pipeline for one Topic under one captured Focus."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Unique Run ID")
    topic_id: str = Field(description="Associated Topic ID")
    channel_id: str = Field(description="Publishing Channel ID (e.g. origins)")
    status: RunStatus = Field(default=RunStatus.PENDING, description="Run lifecycle state")
    captured_focus: FocusSnapshot = Field(
        description="Immutable snapshot of Focus captured at Run creation"
    )
    trace_id: str = Field(description="Distributed trace identifier")
    actor_id: str = Field(description="Actor ID who initiated this Run")
    created_at: datetime = Field(description="Creation timestamp in UTC")
    updated_at: datetime = Field(description="Last state transition timestamp in UTC")
    completed_at: datetime | None = Field(default=None, description="Completion timestamp in UTC")


class Step(BaseModel):
    """One stage within a Run, individually retryable and checkpointed."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Unique Step ID")
    run_id: str = Field(description="Associated Run ID")
    step_name: str = Field(description="Name of pipeline stage (e.g. research, claim_extraction)")
    step_index: int = Field(ge=1, description="Sequential stage order (1..17)")
    status: StepStatus = Field(default=StepStatus.PENDING, description="Step status")
    input_hash: str = Field(description="Hash of step inputs for idempotency verification")
    output_artifact_ref: str | None = Field(
        default=None, description="Reference to output artifact checkpoint"
    )
    error: str | None = Field(default=None, description="Error message if failed")
    started_at: datetime | None = Field(default=None, description="Start timestamp in UTC")
    completed_at: datetime | None = Field(default=None, description="Finish timestamp in UTC")


class Gate(BaseModel):
    """A point where a Run may suspend for approval or verification."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Unique Gate ID")
    run_id: str = Field(description="Associated Run ID")
    step_id: str = Field(description="Associated Step ID")
    gate_type: GateType = Field(description="Gate policy (automatic, manual, hybrid)")
    status: GateStatus = Field(default=GateStatus.PENDING, description="Gate status")
    requested_at: datetime = Field(description="Gate creation timestamp in UTC")
    resolved_at: datetime | None = Field(
        default=None, description="Gate resolution timestamp in UTC"
    )


class Approval(BaseModel):
    """Human decision on a Gate, immutable record."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Unique Approval record ID")
    gate_id: str = Field(description="Associated Gate ID")
    run_id: str = Field(description="Associated Run ID")
    actor_id: str = Field(description="Actor ID who approved or rejected")
    decision: ApprovalDecision = Field(description="Decision outcome")
    feedback: RejectionFeedback | None = Field(
        default=None, description="Required structured feedback on rejection"
    )
    created_at: datetime = Field(description="Decision timestamp in UTC")


class ResourceLock(BaseModel):
    """Named resource lease with TTL (e.g. GPU semaphore)."""

    model_config = ConfigDict(frozen=True)

    resource_name: str = Field(description="Resource name (e.g. gpu)")
    holder_id: str = Field(description="Worker or task identifier holding the lease")
    priority: int = Field(default=0, description="Acquisition priority")
    acquired_at: datetime = Field(description="Acquisition timestamp in UTC")
    expires_at: datetime = Field(description="Lease expiration timestamp in UTC")


class IdempotencyKey(BaseModel):
    """Key enforcing exactly-once Step execution."""

    model_config = ConfigDict(frozen=True)

    key: str = Field(description="Composite key: (run_id:step_name:input_hash)")
    step_id: str = Field(description="Step ID that produced this output")
    output_hash: str = Field(description="Hash of produced output artifact")
    created_at: datetime = Field(description="Creation timestamp in UTC")
    expires_at: datetime | None = Field(default=None, description="Key expiration timestamp in UTC")


class ModelCall(BaseModel):
    """Metered audit record for a language model invocation."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Unique ModelCall ID")
    run_id: str = Field(description="Associated Run ID")
    step_id: str | None = Field(default=None, description="Associated Step ID")
    provider: str = Field(description="Provider name (e.g. gemini, ollama)")
    model_id: str = Field(description="Specific model version identifier")
    prompt_version: str = Field(description="Versioned prompt template ID")
    input_tokens: int = Field(ge=0, description="Input token count")
    output_tokens: int = Field(ge=0, description="Output token count")
    latency_ms: int = Field(ge=0, description="Call latency in milliseconds")
    cached: bool = Field(default=False, description="Whether response came from cache")
    outcome: str = Field(default="success", description="Outcome (success, error, rate_limited)")
    cost_usd: float = Field(default=0.0, ge=0.0, description="Monetary cost ($0 for free tier)")
    created_at: datetime = Field(description="Call timestamp in UTC")


class QuotaLedgerEntry(BaseModel):
    """Append-only consumption ledger entry for quota accounting."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Unique ledger entry ID")
    provider: str = Field(description="Provider identifier")
    window_type: str = Field(description="Window type ('minute' or 'day')")
    window_start: datetime = Field(description="Window boundary start in UTC")
    tokens_consumed: int = Field(ge=0, description="Tokens consumed in window")
    requests_consumed: int = Field(ge=0, description="Requests consumed in window")
    run_id: str | None = Field(default=None, description="Associated Run ID if applicable")
    created_at: datetime = Field(description="Entry timestamp in UTC")
