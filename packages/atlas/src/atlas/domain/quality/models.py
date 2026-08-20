"""Domain models for Quality Evaluation, Rubric Scoring, and Novelty Checking.

As specified in SPEC §8:
- Quality Rubric: 8 dimensions with weights summing to 100%.
- Hard Gate: Weighted total >= 78, no individual dimension < 60, all deterministic checks pass.
- Deterministic checks: Sourcing integrity, duration +/- 2s, loudness -14 LUFS +/- 1, text safe margin, WebVTT captions, novelty.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RubricDimension(StrEnum):
    """The 8 quality evaluation dimensions from SPEC §8.1."""

    SOURCING_INTEGRITY = "sourcing_integrity"
    HOOK_STRENGTH = "hook_strength"
    NARRATIVE_ARC = "narrative_arc"
    LANGUAGE_CRAFT = "language_craft"
    FACTUAL_DENSITY = "factual_density"
    NOVELTY = "novelty"
    VISUAL_COHERENCE = "visual_coherence"
    TECHNICAL_COMPLIANCE = "technical_compliance"


RUBRIC_WEIGHTS: dict[RubricDimension, float] = {
    RubricDimension.SOURCING_INTEGRITY: 20.0,
    RubricDimension.HOOK_STRENGTH: 15.0,
    RubricDimension.NARRATIVE_ARC: 15.0,
    RubricDimension.LANGUAGE_CRAFT: 15.0,
    RubricDimension.FACTUAL_DENSITY: 10.0,
    RubricDimension.NOVELTY: 10.0,
    RubricDimension.VISUAL_COHERENCE: 10.0,
    RubricDimension.TECHNICAL_COMPLIANCE: 5.0,
}


class DimensionScore(BaseModel):
    """Evaluation score for a single rubric dimension."""

    model_config = ConfigDict(frozen=True)

    dimension: RubricDimension = Field(description="Rubric dimension evaluated")
    score: float = Field(ge=0.0, le=100.0, description="Score between 0 and 100")
    weight: float = Field(ge=0.0, le=100.0, description="Dimension weight percentage")
    reason: str = Field(description="Actionable rationale / critique from judge")


class QualityReport(BaseModel):
    """Complete evaluation report produced by the Quality Gate."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Unique Quality Report ID")
    run_id: str = Field(description="Associated Run ID")
    scores: list[DimensionScore] = Field(
        min_length=8, description="Evaluated scores for all 8 dimensions"
    )
    deterministic_checks: dict[str, bool] = Field(
        description="Binary results of deterministic checks (sourcing, duration, loudness, captions)"
    )
    weighted_score: float = Field(ge=0.0, le=100.0, description="Calculated weighted total score")
    passed: bool = Field(description="Whether the render passed all hard gate criteria")
    created_at: datetime = Field(description="Evaluation timestamp in UTC")

    @classmethod
    def evaluate(
        cls,
        report_id: str,
        run_id: str,
        scores: list[DimensionScore],
        deterministic_checks: dict[str, bool],
        created_at: datetime,
    ) -> "QualityReport":
        """Factory method computing weighted score and strict pass/fail status."""
        total_weight = sum(s.weight for s in scores)
        weighted_score = (
            sum((s.score * s.weight) for s in scores) / total_weight if total_weight > 0 else 0.0
        )

        all_deterministic_passed = (
            all(deterministic_checks.values()) if deterministic_checks else False
        )
        no_dimension_below_floor = all(s.score >= 60.0 for s in scores)
        passed_score = weighted_score >= 78.0

        passed = passed_score and no_dimension_below_floor and all_deterministic_passed

        return cls(
            id=report_id,
            run_id=run_id,
            scores=scores,
            deterministic_checks=deterministic_checks,
            weighted_score=round(weighted_score, 2),
            passed=passed,
            created_at=created_at,
        )


class NoveltyResult(BaseModel):
    """Corpus novelty calculation result."""

    model_config = ConfigDict(frozen=True)

    topic_id: str = Field(description="Evaluated Topic ID")
    similarity_score: float = Field(
        ge=0.0, le=1.0, description="Maximum semantic similarity against published corpus"
    )
    is_novel: bool = Field(description="Whether topic meets novelty threshold")
    compared_against_count: int = Field(ge=0, description="Number of published videos checked")
    closest_match_id: str | None = Field(default=None, description="Closest matched topic ID")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Novelty metrics")
