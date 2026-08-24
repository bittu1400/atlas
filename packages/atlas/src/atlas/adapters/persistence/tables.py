"""SQLAlchemy ORM tables for Atlas with strict foreign keys and normalization.

Enforces:
- Row-per-version for Knowledge Objects with stable ko_id and current pointer.
- Normalized foreign-key traceability: Claim -> Evidence -> Source -> Snapshot.
- Impact index for retractions (claim_usages).
- Execution state machine: Runs, Steps, Gates, Approvals.
- Focus model with by-value captured snapshots in Runs.
- Seeded publishing windows and blackout rules from ADR-0007.
"""

from datetime import date, datetime, time
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

# Cross-dialect JSON type that uses JSONB on PostgreSQL and JSON elsewhere
JsonType = JSONB().with_variant(JSON, "sqlite")


class Base(DeclarativeBase):
    """Base declarative class for all Atlas persistence models."""


# ============================================================================
# Knowledge & Traceability Models (ADR-0003, SPEC §3, SPEC §9)
# ============================================================================


class TopicTable(Base):
    """Candidate topic subject table."""

    __tablename__ = "topics"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    domain_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("domains.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    entity_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("entities.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="proposed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('proposed', 'approved', 'researching', 'knowledge_ready', 'blocked', 'rejected', 'published')",
            name="topics_status_check",
        ),
    )


class SourceTable(Base):
    """External document or archive record."""

    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    url: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str | None] = mapped_column(String(256), nullable=True)
    published_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_tier: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    snapshots: Mapped[list["SnapshotTable"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )
    evidence: Mapped[list["EvidenceTable"]] = relationship(
        back_populates="source", overlaps="evidence,snapshot"
    )

    __table_args__ = (
        CheckConstraint(
            "source_tier IN ('primary', 'peer_reviewed', 'institutional', 'reference', 'unvetted')",
            name="sources_source_tier_check",
        ),
    )


class SnapshotTable(Base):
    """Content-addressed archive of retrieved source bytes."""

    __tablename__ = "snapshots"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False, default="text/html")
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    source: Mapped["SourceTable"] = relationship(back_populates="snapshots")
    evidence: Mapped[list["EvidenceTable"]] = relationship(
        back_populates="snapshot", overlaps="evidence,source"
    )

    __table_args__ = (
        Index("ix_snapshots_source_hash", "source_id", "content_hash"),
        UniqueConstraint("id", "source_id", name="uq_snapshot_source"),
        CheckConstraint(
            "storage_key = 'sha256/' || substr(content_hash, 1, 2) || '/' || substr(content_hash, 3, 2) || '/' || content_hash",
            name="snapshots_storage_key_check",
        ),
        CheckConstraint("byte_size >= 0", name="snapshots_byte_size_check"),
    )


class EvidenceTable(Base):
    """Specific verbatim passage supporting or contradicting a Claim."""

    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    snapshot_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    locator: Mapped[str] = mapped_column(String(256), nullable=False)
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    stance: Mapped[str] = mapped_column(String(32), nullable=False, default="supports")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    extracted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    source: Mapped["SourceTable"] = relationship(
        back_populates="evidence", overlaps="evidence,snapshot"
    )
    snapshot: Mapped["SnapshotTable"] = relationship(
        back_populates="evidence", overlaps="evidence,source"
    )
    claim_links: Mapped[list["ClaimEvidenceTable"]] = relationship(back_populates="evidence")

    __table_args__ = (
        CheckConstraint("stance IN ('supports', 'contradicts')", name="evidence_stance_check"),
        CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0", name="evidence_confidence_check"
        ),
        ForeignKeyConstraint(
            ["snapshot_id", "source_id"],
            ["snapshots.id", "snapshots.source_id"],
            ondelete="RESTRICT",
        ),
    )


class ClaimTable(Base):
    """Atomic factual statement."""

    __tablename__ = "claims"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    assertion_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="unsupported", index=True
    )
    inferred_from_claim_ids: Mapped[list[Any]] = mapped_column(
        JsonType, nullable=False, default=list
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    evidence_links: Mapped[list["ClaimEvidenceTable"]] = relationship(
        back_populates="claim", cascade="all, delete-orphan"
    )
    usages: Mapped[list["ClaimUsageTable"]] = relationship(back_populates="claim")

    __table_args__ = (
        CheckConstraint(
            "assertion_type IN ('fact', 'inference', 'opinion', 'contested')",
            name="claims_assertion_type_check",
        ),
        CheckConstraint(
            "status IN ('verified', 'unsupported', 'refuted', 'contested')",
            name="claims_status_check",
        ),
        CheckConstraint("confidence >= 0.0 AND confidence <= 1.0", name="claims_confidence_check"),
    )


class ClaimEvidenceTable(Base):
    """Link table between Claim and supporting/contradicting Evidence."""

    __tablename__ = "claim_evidence"

    claim_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("claims.id", ondelete="CASCADE"), primary_key=True
    )
    evidence_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("evidence.id", ondelete="RESTRICT"), primary_key=True
    )
    stance: Mapped[str] = mapped_column(String(32), nullable=False, default="supports")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    claim: Mapped["ClaimTable"] = relationship(back_populates="evidence_links")
    evidence: Mapped["EvidenceTable"] = relationship(back_populates="claim_links")

    __table_args__ = (
        CheckConstraint(
            "stance IN ('supports', 'contradicts')", name="claim_evidence_stance_check"
        ),
    )


class KnowledgeObjectVersionTable(Base):
    """Row-per-version immutable Knowledge Object revision."""

    __tablename__ = "knowledge_object_versions"

    ko_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("topics.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    entity_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("entities.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    actor_id: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    claims: Mapped[list["KnowledgeObjectClaimTable"]] = relationship(
        back_populates="ko_version", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("ko_id", "version", name="uq_ko_version"),
        CheckConstraint(
            "status IN ('draft', 'verified', 'published', 'archived')",
            name="ko_status_check",
        ),
        CheckConstraint("confidence >= 0.0 AND confidence <= 1.0", name="kov_confidence_check"),
        CheckConstraint(
            "quality_score IS NULL OR (quality_score >= 0.0 AND quality_score <= 100.0)",
            name="kov_quality_score_check",
        ),
    )


class KnowledgeObjectCurrentTable(Base):
    """Pointer table identifying the current active version of each Knowledge Object."""

    __tablename__ = "knowledge_object_current"

    ko_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    current_version: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["ko_id", "current_version"],
            ["knowledge_object_versions.ko_id", "knowledge_object_versions.version"],
            ondelete="RESTRICT",
        ),
    )


class KnowledgeObjectClaimTable(Base):
    """Link table between a Knowledge Object version and its associated Claims."""

    __tablename__ = "knowledge_object_claims"

    ko_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    claim_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("claims.id", ondelete="RESTRICT"), primary_key=True
    )

    ko_version: Mapped["KnowledgeObjectVersionTable"] = relationship(back_populates="claims")

    __table_args__ = (
        ForeignKeyConstraint(
            ["ko_id", "version"],
            ["knowledge_object_versions.ko_id", "knowledge_object_versions.version"],
            ondelete="CASCADE",
        ),
    )


class ClaimUsageTable(Base):
    """Impact index mapping Claim to published render beats for retraction and corrections."""

    __tablename__ = "claim_usages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    claim_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("claims.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    render_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    beat_id: Mapped[str] = mapped_column(String(64), nullable=False)
    used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    claim: Mapped["ClaimTable"] = relationship(back_populates="usages")


# ============================================================================
# Focus & Domain Models (ADR-0002)
# ============================================================================


class DomainTable(Base):
    """Knowledge domain with research policy."""

    __tablename__ = "domains"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    research_profile: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False)


class EntityTable(Base):
    """Canonical externally-anchored entity."""

    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    wikidata_qid: Mapped[str | None] = mapped_column(
        String(32), nullable=True, index=True, unique=True
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    domain_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("domains.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    aliases: Mapped[list[Any]] = mapped_column(JsonType, nullable=False, default=list)


class FocusTable(Base):
    """Versioned Focus record holding facets."""

    __tablename__ = "focus"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    scope_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="soft")
    facets: Mapped[list[Any]] = mapped_column(JsonType, nullable=False, default=list)
    entity_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("entities.id", ondelete="SET NULL"), nullable=True
    )
    actor_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "scope_mode IN ('hard', 'soft', 'exploratory')", name="focus_scope_mode_check"
        ),
    )


class ActiveFocusTable(Base):
    """Singleton pointer to the active Focus supplying default for new Runs."""

    __tablename__ = "active_focus"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default="default")
    focus_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("focus.id", ondelete="RESTRICT"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(64), nullable=False)


# ============================================================================
# Channel & Publishing Windows Models (ADR-0007)
# ============================================================================


class ChannelTable(Base):
    """Publishing identity with audience timezone."""

    __tablename__ = "channels"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    audience_timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, default="America/New_York"
    )
    style_profile: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    publishing_windows: Mapped[list["PublishingWindowTable"]] = relationship(
        back_populates="channel", cascade="all, delete-orphan"
    )


class PublishingWindowTable(Base):
    """Publishing windows seeded as priors or learned from analytics."""

    __tablename__ = "publishing_windows"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    channel_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("channels.id", ondelete="CASCADE"), nullable=False, index=True
    )
    platform: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    content_format: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    local_start_time: Mapped[time] = mapped_column(Time, nullable=False)
    local_end_time: Mapped[time] = mapped_column(Time, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    source: Mapped[str] = mapped_column(String(256), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.8)

    channel: Mapped["ChannelTable"] = relationship(back_populates="publishing_windows")

    __table_args__ = (
        Index("ix_pub_windows_lookup", "channel_id", "platform", "content_format", "day_of_week"),
        CheckConstraint(
            "day_of_week >= 0 AND day_of_week <= 6", name="pub_windows_day_of_week_check"
        ),
        CheckConstraint("rank >= 1", name="pub_windows_rank_check"),
        CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0", name="pub_windows_confidence_check"
        ),
    )


class BlackoutRuleTable(Base):
    """Enforced blackout rule prohibiting publishing during sleep hours."""

    __tablename__ = "blackout_rules"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    earliest_allowed_time: Mapped[time] = mapped_column(Time, nullable=False)
    latest_allowed_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_enforced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


# ============================================================================
# Pipeline Execution State Machine Models (ADR-0001, ADR-0004)
# ============================================================================


class RunTable(Base):
    """Run entity capturing focus by value."""

    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    topic_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("topics.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    channel_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("channels.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    captured_focus: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor_id: Mapped[str] = mapped_column(String(64), nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    steps: Mapped[list["StepTable"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    gates: Mapped[list["GateTable"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'suspended', 'reworking', 'completed', 'failed', 'abandoned')",
            name="runs_status_check",
        ),
    )


class StepTable(Base):
    """Step execution state with idempotency input hash."""

    __tablename__ = "steps"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    output_artifact_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    run: Mapped["RunTable"] = relationship(back_populates="steps")
    gates: Mapped[list["GateTable"]] = relationship(
        back_populates="step",
        foreign_keys="[GateTable.step_id, GateTable.run_id]",
        overlaps="gates,step,run",
    )

    __table_args__ = (
        Index("ix_steps_idempotency", "run_id", "step_name", "input_hash", unique=True),
        UniqueConstraint("id", "run_id", name="uq_step_run"),
        CheckConstraint(
            "status IN ('pending', 'running', 'suspended', 'succeeded', 'failed', 'skipped')",
            name="steps_status_check",
        ),
    )


class GateTable(Base):
    """Gate row where a Run suspends for manual or hybrid resolution."""

    __tablename__ = "gates"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    gate_type: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    run: Mapped["RunTable"] = relationship(back_populates="gates", overlaps="gates,step,run")
    step: Mapped["StepTable"] = relationship(
        back_populates="gates",
        foreign_keys="[GateTable.step_id, GateTable.run_id]",
        overlaps="gates,step,run",
    )
    approvals: Mapped[list["ApprovalTable"]] = relationship(
        back_populates="gate",
        cascade="all, delete-orphan",
        foreign_keys="[ApprovalTable.gate_id, ApprovalTable.run_id]",
        overlaps="approvals,gate,run",
    )

    __table_args__ = (
        CheckConstraint("gate_type IN ('automatic', 'manual', 'hybrid')", name="gates_type_check"),
        CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="gates_status_check"),
        ForeignKeyConstraint(
            ["step_id", "run_id"], ["steps.id", "steps.run_id"], ondelete="CASCADE"
        ),
        UniqueConstraint("id", "run_id", name="uq_gate_run"),
    )


class ApprovalTable(Base):
    """Approval or structured rejection decision record."""

    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    gate_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_id: Mapped[str] = mapped_column(String(64), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    feedback: Mapped[dict[str, Any] | None] = mapped_column(JsonType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    gate: Mapped["GateTable"] = relationship(
        back_populates="approvals",
        foreign_keys="[ApprovalTable.gate_id, ApprovalTable.run_id]",
        overlaps="approvals,gate,run",
    )

    __table_args__ = (
        CheckConstraint("decision IN ('approved', 'rejected')", name="approvals_decision_check"),
        ForeignKeyConstraint(
            ["gate_id", "run_id"], ["gates.id", "gates.run_id"], ondelete="CASCADE"
        ),
        UniqueConstraint("gate_id", name="uq_approval_gate"),
    )


class ResourceLockTable(Base):
    """Named resource semaphore (e.g. GPU lease)."""

    __tablename__ = "resource_locks"

    resource_name: Mapped[str] = mapped_column(String(64), primary_key=True)
    holder_id: Mapped[str] = mapped_column(String(128), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )


class IdempotencyKeyTable(Base):
    """Step idempotency store."""

    __tablename__ = "idempotency_keys"

    key: Mapped[str] = mapped_column(String(256), primary_key=True)
    step_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("steps.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    output_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )


class ModelCallTable(Base):
    """Metered audit log for every model call."""

    __tablename__ = "model_calls"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    model_id: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    code_version: Mapped[str] = mapped_column(String(64), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cached: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False, default="success")
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    __table_args__ = (
        CheckConstraint(
            "outcome IN ('success', 'error', 'rate_limited')", name="model_calls_outcome_check"
        ),
        CheckConstraint("input_tokens >= 0", name="model_calls_input_tokens_check"),
        CheckConstraint("output_tokens >= 0", name="model_calls_output_tokens_check"),
        CheckConstraint("latency_ms >= 0", name="model_calls_latency_ms_check"),
        CheckConstraint("cost_usd >= 0.0", name="model_calls_cost_usd_check"),
        ForeignKeyConstraint(
            ["step_id", "run_id"], ["steps.id", "steps.run_id"], ondelete="RESTRICT"
        ),
    )


class QuotaLedgerTable(Base):
    """Append-only quota consumption ledger."""

    __tablename__ = "quota_ledger"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    window_type: Mapped[str] = mapped_column(String(32), nullable=False)
    window_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    tokens_consumed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    requests_consumed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    run_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("runs.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_quota_window", "provider", "window_type", "window_start"),
        CheckConstraint("window_type IN ('minute', 'day')", name="quota_window_type_check"),
        CheckConstraint("tokens_consumed >= 0", name="quota_tokens_consumed_check"),
        CheckConstraint("requests_consumed >= 0", name="quota_requests_consumed_check"),
    )
