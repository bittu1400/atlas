"""FastAPI Request and Response Data Transfer Objects (DTOs)."""

from datetime import datetime
from typing import Any

from atlas.domain.execution.models import (
    ApprovalDecision,
    GateStatus,
    GateType,
    RejectionAction,
    RunStatus,
    StepStatus,
)
from pydantic import BaseModel, Field


class CreateRunRequest(BaseModel):
    """Payload for creating a new pipeline Run."""

    topic_id: str = Field(description="Unique Topic identifier (e.g. topic_origin_of_chess)")
    channel_id: str = Field(default="origins", description="Publishing channel identifier")
    actor_id: str = Field(default="operator", description="Actor initiating the run")
    focus_id: str | None = Field(
        default=None, description="Optional Focus ID; defaults to active focus"
    )


class RunResponse(BaseModel):
    """Response representing a pipeline Run."""

    id: str
    topic_id: str
    channel_id: str
    status: RunStatus
    captured_focus: dict[str, Any]
    trace_id: str
    actor_id: str
    error: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class StepResponse(BaseModel):
    """Response representing an individual Step."""

    id: str
    run_id: str
    step_name: str
    step_index: int
    status: StepStatus
    input_hash: str
    output_artifact_ref: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class GateResponse(BaseModel):
    """Response representing a suspension Gate."""

    id: str
    run_id: str
    step_id: str
    gate_type: GateType
    status: GateStatus
    requested_at: datetime
    resolved_at: datetime | None = None


class ApproveGateRequest(BaseModel):
    """Payload for approving a pending Gate."""

    actor_id: str = Field(default="operator", description="Actor granting approval")


class RejectGateRequest(BaseModel):
    """Payload for rejecting a Gate with mandatory structured feedback (SPEC §7)."""

    target_ref: str = Field(description="Target identifier (e.g. Beat ID, Asset ID)")
    rubric_dimension: str = Field(description="Rubric dimension failed")
    reason: str = Field(description="Specific actionable critique")
    action: RejectionAction = Field(
        default=RejectionAction.REGENERATE,
        description="Next action: regenerate, branch, or abandon",
    )
    actor_id: str = Field(default="operator", description="Actor rejecting the gate")


class ApprovalResponse(BaseModel):
    """Response representing an Approval record."""

    id: str
    gate_id: str
    run_id: str
    actor_id: str
    decision: ApprovalDecision
    feedback: dict[str, Any] | None = None
    created_at: datetime


class QuotaStatusResponse(BaseModel):
    """Response summarizing quota usage."""

    status: str
    providers: dict[str, Any]
