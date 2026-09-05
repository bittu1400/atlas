"""Domain models for the Knowledge System and Traceability Chain.

Invariants strictly enforced:
- Invariant 1: Every statement resolves Claim -> Evidence -> Source -> Snapshot.
- Invariant 2: A model is never the source of a fact. Unsupported claims are dropped.
- Invariant 3: Claims carry an AssertionType (fact, inference, opinion, contested).
- Invariant 4: Knowledge is append-only.
- ADR-0003: Row-per-version with current pointer and normalized foreign-key traceability.
"""

from datetime import date, datetime
from enum import StrEnum

from atlas.domain.common.enums import SourceTier
from atlas.domain.knowledge.payload import KnowledgePayloadV1
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class AssertionType(StrEnum):
    """Type of claim assertion as defined in SPEC §3."""

    FACT = "fact"
    INFERENCE = "inference"
    OPINION = "opinion"
    CONTESTED = "contested"


class ClaimStatus(StrEnum):
    """Verification status of a Claim."""

    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    UNSUPPORTED = "unsupported"
    REFUTED = "refuted"
    CONTESTED = "contested"


class EvidenceStance(StrEnum):
    """Stance of evidence toward a claim."""

    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"


class KnowledgeObjectStatus(StrEnum):
    """Lifecycle status of a Knowledge Object version."""

    DRAFT = "draft"
    VERIFIED = "verified"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class TopicStatus(StrEnum):
    """Lifecycle status of a Topic."""

    PROPOSED = "proposed"
    APPROVED = "approved"
    RESEARCHING = "researching"
    KNOWLEDGE_READY = "knowledge_ready"
    BLOCKED = "blocked"
    REJECTED = "rejected"
    PUBLISHED = "published"


class Topic(BaseModel):
    """Candidate subject for one output."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Unique Topic identifier")
    title: str = Field(description="Topic title / subject headline")
    domain_id: str = Field(description="Associated Domain ID")
    entity_id: str | None = Field(default=None, description="Resolved Wikidata QID or Entity ID")
    status: TopicStatus = Field(default=TopicStatus.PROPOSED, description="Lifecycle status")
    created_at: datetime = Field(description="Creation timestamp in UTC")


class Source(BaseModel):
    """Retrievable external document or archive record."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Unique Source identifier")
    url: HttpUrl = Field(description="Source URL or permanent identifier")
    title: str = Field(description="Document title")
    author: str | None = Field(default=None, description="Author or publishing institution")
    published_date: date | None = Field(default=None, description="Publication date if available")
    source_tier: SourceTier = Field(description="Authority tier")
    created_at: datetime = Field(description="Creation timestamp in UTC")


class Snapshot(BaseModel):
    """Archived bytes of a retrieved Source, content-addressed by SHA-256."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Unique Snapshot identifier")
    source_id: str = Field(description="Source ID this snapshot archives")
    content_hash: str = Field(
        pattern=r"^[a-f0-9]{64}$", description="SHA-256 hash of retrieved payload"
    )
    storage_key: str = Field(description="Content-addressed storage locator")
    mime_type: str = Field(default="text/html", description="MIME type of stored payload")
    byte_size: int = Field(ge=0, description="Size in bytes")
    retrieved_at: datetime = Field(description="Retrieval timestamp in UTC")


class Evidence(BaseModel):
    """Specific passage in a Source + Snapshot supporting or contradicting a Claim."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Unique Evidence identifier")
    source_id: str = Field(description="Foreign key to Source")
    snapshot_id: str = Field(description="Foreign key to Snapshot")
    locator: str = Field(description="Page, offset, xpath, or quote locator")
    quote: str = Field(description="Exact verbatim excerpt from snapshot")
    stance: EvidenceStance = Field(default=EvidenceStance.SUPPORTS, description="Support stance")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction confidence")
    extracted_at: datetime = Field(description="Extraction timestamp in UTC")


class Claim(BaseModel):
    """Atomic factual statement with strict evidence linkage."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Unique Claim identifier")
    version: int = Field(
        default=1, ge=1, description="Append-only revision number of this claim's state"
    )
    text: str = Field(description="Atomic claim statement")
    assertion_type: AssertionType = Field(description="Assertion type")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Claim confidence score")
    status: ClaimStatus = Field(default=ClaimStatus.UNSUPPORTED, description="Verification status")
    inferred_from_claim_ids: list[str] = Field(
        default_factory=list, description="Parent claim IDs if assertion_type is inference"
    )
    created_at: datetime = Field(description="Creation timestamp in UTC")


class ClaimEvidenceLink(BaseModel):
    """Link between a Claim and supporting or contradicting Evidence."""

    model_config = ConfigDict(frozen=True)

    claim_id: str = Field(description="Claim ID")
    evidence_id: str = Field(description="Evidence ID")
    stance: EvidenceStance = Field(default=EvidenceStance.SUPPORTS, description="Evidence stance")
    notes: str | None = Field(default=None, description="Verification commentary")


class KnowledgeObjectVersion(BaseModel):
    """One immutable revision of a Knowledge Object sharing a stable ko_id."""

    model_config = ConfigDict(frozen=True)

    ko_id: str = Field(description="Stable Knowledge Object ID across all revisions")
    version: int = Field(ge=1, description="Sequential revision number (1, 2, 3...)")
    topic_id: str = Field(description="Associated Topic ID")
    entity_id: str | None = Field(default=None, description="Anchored Entity QID")
    status: KnowledgeObjectStatus = Field(default=KnowledgeObjectStatus.DRAFT, description="Status")
    quality_score: float | None = Field(
        default=None, ge=0.0, le=100.0, description="Overall quality score"
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Knowledge confidence score")
    actor_id: str = Field(description="Actor identifier who created this revision")
    reason: str = Field(description="Reason for revision or genesis rationale")
    payload: KnowledgePayloadV1 = Field(
        description="Versioned JSONB payload carrying exploratory fields"
    )
    claim_ids: list[str] = Field(
        default_factory=list, description="Claim IDs included in this version"
    )
    created_at: datetime = Field(description="Revision timestamp in UTC")


class ClaimUsage(BaseModel):
    """Impact index mapping Claim to published render beats for retraction and corrections."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Unique usage record ID")
    claim_id: str = Field(description="Claim ID")
    render_id: str = Field(description="Published Render ID")
    beat_id: str = Field(description="Script Beat ID where claim was asserted")
    used_at: datetime = Field(description="Usage timestamp in UTC")


class TraceabilityChain(BaseModel):
    """Resolved traceability tree for a Claim."""

    model_config = ConfigDict(frozen=True)

    claim: Claim
    evidence_with_sources: list[tuple[ClaimEvidenceLink, Evidence, Source, Snapshot]]
