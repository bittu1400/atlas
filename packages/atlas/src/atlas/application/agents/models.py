"""Structured Pydantic schemas for Agent LLM structured extractions."""

from atlas.domain.knowledge.models import AssertionType, EvidenceStance
from atlas.domain.quality.models import RubricDimension
from pydantic import BaseModel, ConfigDict, Field


class ExtractedClaimItem(BaseModel):
    """An atomic claim extracted by the Extraction Agent."""

    model_config = ConfigDict(frozen=True)

    text: str = Field(description="Atomic factual or analytical statement")
    assertion_type: AssertionType = Field(
        default=AssertionType.FACT, description="Type of assertion"
    )
    confidence: float = Field(default=0.9, ge=0.0, le=1.0, description="Extraction confidence")


class ExtractedEvidenceItem(BaseModel):
    """A primary evidence quote extracted from source text."""

    model_config = ConfigDict(frozen=True)

    locator: str = Field(description="Locator in document, e.g. section, paragraph, or page")
    quote: str = Field(description="Exact verbatim quote from source snapshot")
    stance: EvidenceStance = Field(
        default=EvidenceStance.SUPPORTS, description="Stance towards the assertion"
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction confidence")


class ExtractedLinkItem(BaseModel):
    """Link mapping an extracted claim to its cited evidence."""

    model_config = ConfigDict(frozen=True)

    claim_index: int = Field(ge=0, description="0-indexed position in extracted claims list")
    evidence_index: int = Field(ge=0, description="0-indexed position in extracted evidence list")
    stance: EvidenceStance = Field(default=EvidenceStance.SUPPORTS, description="Evidence stance")
    notes: str | None = Field(default=None, description="Optional notes on the link")


class ExtractionPayload(BaseModel):
    """Full structured extraction payload returned by LLM."""

    model_config = ConfigDict(frozen=True)

    claims: list[ExtractedClaimItem] = Field(
        default_factory=list, description="Extracted atomic claims"
    )
    evidence: list[ExtractedEvidenceItem] = Field(
        default_factory=list, description="Extracted supporting evidence quotes"
    )
    links: list[ExtractedLinkItem] = Field(
        default_factory=list, description="Explicit claim-to-evidence links"
    )


class VerificationResultItem(BaseModel):
    """Result of cross-examining an individual claim against its cited evidence quote."""

    model_config = ConfigDict(frozen=True)

    status: str = Field(
        default="verified",
        description="Verification outcome: verified, unsupported, refuted, contested",
    )
    stance: EvidenceStance = Field(default=EvidenceStance.SUPPORTS, description="Evidence stance")
    rationale: str = Field(description="Concise rationale for verification decision")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Verification confidence")


class VerificationPayload(BaseModel):
    """Batch verification payload returned by Verification Agent."""

    model_config = ConfigDict(frozen=True)

    verifications: list[VerificationResultItem] = Field(
        default_factory=list, description="Verification results for examined claims"
    )


class TopicIdeaItem(BaseModel):
    """Topic candidate proposal."""

    model_config = ConfigDict(frozen=True)

    title: str = Field(description="Headline topic title")
    rationale: str = Field(description="Why this topic fits focus and has archival assets")
    search_queries: list[str] = Field(
        default_factory=list, description="Search queries for primary archives"
    )
    estimated_novelty: float = Field(default=0.8, ge=0.0, le=1.0, description="Estimated novelty")


class TopicDiscoveryPayload(BaseModel):
    """Candidate topics payload from discovery."""

    model_config = ConfigDict(frozen=True)

    topics: list[TopicIdeaItem] = Field(
        min_length=1, description="List of proposed documentary topics"
    )


class StoryAngleItem(BaseModel):
    """Narrative angle option."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(description="Short angle label")
    hook: str = Field(description="Opening premise")
    narrative_thesis: str = Field(description="Central insight / thesis")
    score: float = Field(ge=0.0, le=100.0, description="Calculated angle rating")


class StoryAnglePayload(BaseModel):
    """Angles evaluated for scriptwriting."""

    model_config = ConfigDict(frozen=True)

    angles: list[StoryAngleItem] = Field(min_length=1, description="Candidate angles evaluated")
    selected_angle: str = Field(description="Name of the selected best angle")
    selection_reason: str = Field(description="Rationale for choosing selected angle")


class ScriptBeatItem(BaseModel):
    """Individual beat in generated script."""

    model_config = ConfigDict(frozen=True)

    beat_index: int = Field(ge=1, description="1-indexed sequence order")
    text: str = Field(description="Kinetic on-screen text")
    claim_ids: list[str] = Field(
        min_length=1, description="Traceable claim IDs substantiating this beat"
    )
    duration_seconds: float = Field(
        default=3.5, ge=0.5, le=10.0, description="Dwell time in seconds"
    )
    visual_cue: str | None = Field(
        default=None, description="Visual description for archival asset search"
    )


class ScriptPayload(BaseModel):
    """Structured script output."""

    model_config = ConfigDict(frozen=True)

    beats: list[ScriptBeatItem] = Field(
        min_length=1, description="Ordered sequence of script beats"
    )


class JudgeScoreItem(BaseModel):
    """Evaluation score for one rubric dimension."""

    model_config = ConfigDict(frozen=True)

    dimension: RubricDimension = Field(description="Rubric dimension evaluated")
    score: float = Field(ge=0.0, le=100.0, description="Score 0 to 100")
    reason: str = Field(description="Critical actionable feedback")


class QualityJudgePayload(BaseModel):
    """Complete rubric evaluation output from judge."""

    model_config = ConfigDict(frozen=True)

    scores: list[JudgeScoreItem] = Field(
        min_length=8, description="Evaluated scores for all 8 dimensions"
    )
