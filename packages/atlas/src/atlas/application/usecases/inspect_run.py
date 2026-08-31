"""Read-only use cases that expose what a Run actually produced.

The operator dashboard used to draw its Knowledge and Telemetry panels from
hardcoded arrays — invented claims, invented snapshot hashes, invented log
lines (defect V-03). These two use cases are what those panels read instead, so
what an operator sees on screen is a row in the database or nothing at all.
"""

from datetime import datetime

from atlas.application.ports.repositories import (
    ExecutionRepositoryPort,
    KnowledgeRepositoryPort,
)
from atlas.domain.knowledge.models import (
    AssertionType,
    ClaimStatus,
    EvidenceStance,
)
from pydantic import BaseModel, ConfigDict, Field


class EvidenceView(BaseModel):
    """One Evidence row resolved to its Source and Snapshot."""

    model_config = ConfigDict(frozen=True)

    evidence_id: str
    quote: str
    locator: str
    stance: EvidenceStance
    source_id: str
    source_title: str
    source_url: str
    source_tier: str
    snapshot_id: str
    snapshot_sha256: str = Field(description="SHA-256 of the archived bytes the quote came from")
    retrieved_at: datetime


class ClaimView(BaseModel):
    """One Claim with its full traceability chain resolved."""

    model_config = ConfigDict(frozen=True)

    claim_id: str
    version: int
    text: str
    assertion_type: AssertionType
    status: ClaimStatus
    confidence: float
    evidence: list[EvidenceView]


class RunKnowledgeView(BaseModel):
    """The current Knowledge Object for a Run's Topic, fully traced."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    topic_id: str
    ko_id: str | None = None
    ko_version: int | None = None
    claims: list[ClaimView] = Field(default_factory=list)


class TelemetryEvent(BaseModel):
    """One thing that actually happened during a Run, in time order."""

    model_config = ConfigDict(frozen=True)

    id: str
    timestamp: datetime
    kind: str = Field(description="'step' or 'model_call'")
    stage: str
    event: str
    status: str
    detail: dict[str, str] = Field(default_factory=dict)


class GetRunKnowledgeUseCase:
    """Resolve a Run's Knowledge Object down to evidence, sources and snapshots."""

    def __init__(
        self,
        execution_repo: ExecutionRepositoryPort,
        knowledge_repo: KnowledgeRepositoryPort,
    ) -> None:
        self.execution_repo = execution_repo
        self.knowledge_repo = knowledge_repo

    async def execute(self, run_id: str) -> RunKnowledgeView:
        """Return every Claim in the Run's current Knowledge Object with its chain.

        A Run whose extraction stage has not run yet has no Knowledge Object.
        That is reported as an empty claim list, never as a placeholder claim.
        """
        run = await self.execution_repo.get_run(run_id)
        ko = await self.knowledge_repo.get_current_for_topic(run.topic_id)
        if ko is None:
            return RunKnowledgeView(run_id=run_id, topic_id=run.topic_id)

        claims: list[ClaimView] = []
        for claim_id in ko.claim_ids:
            chain = await self.knowledge_repo.get_traceability_chain(claim_id)
            claims.append(
                ClaimView(
                    claim_id=chain.claim.id,
                    version=chain.claim.version,
                    text=chain.claim.text,
                    assertion_type=chain.claim.assertion_type,
                    status=chain.claim.status,
                    confidence=chain.claim.confidence,
                    evidence=[
                        EvidenceView(
                            evidence_id=evidence.id,
                            quote=evidence.quote,
                            locator=evidence.locator,
                            stance=link.stance,
                            source_id=source.id,
                            source_title=source.title,
                            source_url=str(source.url),
                            source_tier=source.source_tier.value,
                            snapshot_id=snapshot.id,
                            snapshot_sha256=snapshot.content_hash,
                            retrieved_at=snapshot.retrieved_at,
                        )
                        for link, evidence, source, snapshot in chain.evidence_with_sources
                    ],
                )
            )

        return RunKnowledgeView(
            run_id=run_id,
            topic_id=run.topic_id,
            ko_id=ko.ko_id,
            ko_version=ko.version,
            claims=claims,
        )


class GetRunTelemetryUseCase:
    """Merge a Run's Steps and metered model calls into one time-ordered stream."""

    def __init__(self, execution_repo: ExecutionRepositoryPort) -> None:
        self.execution_repo = execution_repo

    async def execute(self, run_id: str, limit: int = 100) -> list[TelemetryEvent]:
        """Return the Run's recorded activity, newest first."""
        steps = await self.execution_repo.list_steps_for_run(run_id)
        model_calls = await self.execution_repo.list_model_calls_for_run(run_id)

        events: list[TelemetryEvent] = []
        for step in steps:
            timestamp = step.completed_at or step.started_at
            if timestamp is None:
                continue
            events.append(
                TelemetryEvent(
                    id=step.id,
                    timestamp=timestamp,
                    kind="step",
                    stage=step.step_name,
                    event=step.error or f"Step {step.step_index} of 18 {step.status.value}",
                    status=step.status.value,
                    detail=(
                        {"output_artifact_ref": step.output_artifact_ref}
                        if step.output_artifact_ref
                        else {}
                    ),
                )
            )

        for call in model_calls:
            events.append(
                TelemetryEvent(
                    id=call.id,
                    timestamp=call.created_at,
                    kind="model_call",
                    stage=call.prompt_version,
                    event=f"{call.provider}/{call.model_id} metered",
                    status=call.outcome,
                    detail={
                        "input_tokens": str(call.input_tokens),
                        "output_tokens": str(call.output_tokens),
                        "latency_ms": str(call.latency_ms),
                        "cached": str(call.cached).lower(),
                    },
                )
            )

        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[:limit]
