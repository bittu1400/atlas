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
from atlas.domain.focus.models import ScopeMode
from atlas.domain.knowledge.models import TopicStatus
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


# =============================================================================
# The rows a Run needs before it can exist (T-64)
#
# The dashboard's Launch form used to be three free-text boxes over IDs only
# the terminal could reveal. These are what the pickers read and write.
# =============================================================================


class CreateDomainRequest(BaseModel):
    """Payload for registering a Domain and its Research Profile."""

    id: str = Field(description="Unique Domain ID (e.g. dom_history)")
    name: str = Field(description="Display name (e.g. History)")
    description: str = Field(description="What this Domain covers")


class DomainResponse(BaseModel):
    """A Domain and the Research Profile that makes it more than a tag."""

    id: str
    name: str
    description: str
    research_profile: dict[str, Any]


class CreateTopicRequest(BaseModel):
    """Payload for registering a Topic against an existing Domain."""

    id: str = Field(description="Unique Topic ID (e.g. topic_origin_of_chess)")
    title: str = Field(description="Human-readable Topic title")
    domain_id: str = Field(description="Existing Domain ID")
    entity_id: str | None = Field(default=None, description="Wikidata QID, if resolved")


class TopicResponse(BaseModel):
    """A candidate subject for one output."""

    id: str
    title: str
    domain_id: str
    entity_id: str | None
    status: TopicStatus
    created_at: datetime


class CreateChannelRequest(BaseModel):
    """Payload for registering a publishing Channel."""

    id: str = Field(description="Unique Channel ID (e.g. origins)")
    name: str = Field(description="Display name")
    audience_timezone: str = Field(
        default="America/New_York", description="IANA timezone of the Channel's audience"
    )
    style_profile: dict[str, Any] = Field(
        default_factory=dict, description="Style Profile crafting parameters"
    )


class ChannelResponse(BaseModel):
    """A publishing identity carrying a Style Profile and an audience clock."""

    id: str
    name: str
    audience_timezone: str
    style_profile: dict[str, Any]
    created_at: datetime


class FacetPayload(BaseModel):
    """One typed `(dimension, value)` constraint inside a Focus."""

    dimension: str = Field(description="Facet dimension, e.g. domain or subject")
    value: str = Field(description="Facet value")


class CreateFocusRequest(BaseModel):
    """Payload for registering a Focus.

    No ID: a Focus is immutable and versioned by creation, so its ID is
    generated rather than chosen.
    """

    name: str = Field(description="Operator-facing Focus name")
    facets: list[FacetPayload] = Field(description="The constraints this Focus carries")
    scope_mode: ScopeMode = Field(
        default=ScopeMode.SOFT, description="hard, soft or exploratory (SPEC §4)"
    )
    entity_id: str | None = Field(default=None, description="Resolved Entity, if any")
    actor_id: str = Field(default="operator", description="Actor creating the Focus")
