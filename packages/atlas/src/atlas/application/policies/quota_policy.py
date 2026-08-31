"""Provider Routing and Task-to-Tier Allocation Policy.

As specified in ADR-0004:
- Tier 0: Free deterministic APIs (Wikidata, OpenAlex, Smithsonian) -> all facts and archival imagery.
- Tier 1: Local GPU models -> classification, dedup, entity extraction, summarization drafts.
- Tier 2: Hosted free-tier frontier models -> claim extraction fidelity, beat writing, quality judging.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class TaskKind(StrEnum):
    """Categorized task kinds in the pipeline."""

    RETRIEVAL = "retrieval"
    TOPIC_DISCOVERY = "topic_discovery"
    EMBEDDING = "embedding"
    ENTITY_EXTRACTION = "entity_extraction"
    CLAIM_EXTRACTION = "claim_extraction"
    VERIFICATION = "verification"
    STORY_ANGLE_GENERATION = "story_angle_generation"
    SCRIPT_WRITING = "script_writing"
    TIMING_CALCULATION = "timing_calculation"
    QUALITY_JUDGING = "quality_judging"
    IMAGE_GENERATION = "image_generation"


class ModelRoute(BaseModel):
    """Routing configuration for a task kind."""

    model_config = ConfigDict(frozen=True)

    task: TaskKind
    tier: int = Field(description="Tier level (0, 1, or 2)")
    provider: str = Field(description="Provider name (gemini, ollama, fake)")
    model_id: str = Field(description="Target model ID")
    temperature: float = Field(default=0.7)
    max_tokens: int | None = Field(default=2048)


class RoutingPolicy:
    """Selects the target tier and provider based on task kind."""

    DEFAULT_ROUTES: dict[TaskKind, ModelRoute] = {
        TaskKind.RETRIEVAL: ModelRoute(
            task=TaskKind.RETRIEVAL, tier=0, provider="fake", model_id="none", max_tokens=None
        ),
        TaskKind.TOPIC_DISCOVERY: ModelRoute(
            task=TaskKind.TOPIC_DISCOVERY,
            tier=2,
            provider="gemini",
            model_id="gemini-2.0-flash",
            temperature=0.8,
            max_tokens=2048,
        ),
        TaskKind.EMBEDDING: ModelRoute(
            task=TaskKind.EMBEDDING,
            tier=1,
            provider="ollama",
            model_id="nomic-embed-text",
            temperature=0.0,
            max_tokens=None,
        ),
        TaskKind.ENTITY_EXTRACTION: ModelRoute(
            task=TaskKind.ENTITY_EXTRACTION,
            tier=1,
            provider="ollama",
            model_id="qwen3:8b",
            temperature=0.2,
            max_tokens=2048,
        ),
        TaskKind.CLAIM_EXTRACTION: ModelRoute(
            task=TaskKind.CLAIM_EXTRACTION,
            tier=2,
            provider="gemini",
            model_id="gemini-2.0-flash",
            temperature=0.2,
            max_tokens=4096,
        ),
        TaskKind.VERIFICATION: ModelRoute(
            task=TaskKind.VERIFICATION,
            tier=2,
            provider="gemini",
            model_id="gemini-2.0-flash",
            temperature=0.0,
            max_tokens=2048,
        ),
        TaskKind.STORY_ANGLE_GENERATION: ModelRoute(
            task=TaskKind.STORY_ANGLE_GENERATION,
            tier=2,
            provider="gemini",
            model_id="gemini-2.0-flash",
            temperature=0.8,
            max_tokens=2048,
        ),
        TaskKind.SCRIPT_WRITING: ModelRoute(
            task=TaskKind.SCRIPT_WRITING,
            tier=2,
            provider="gemini",
            model_id="gemini-2.0-flash",
            temperature=0.7,
            max_tokens=2048,
        ),
        TaskKind.TIMING_CALCULATION: ModelRoute(
            task=TaskKind.TIMING_CALCULATION,
            tier=0,
            provider="fake",
            model_id="none",
            max_tokens=None,
        ),
        TaskKind.QUALITY_JUDGING: ModelRoute(
            task=TaskKind.QUALITY_JUDGING,
            tier=2,
            provider="gemini",
            model_id="gemini-2.0-flash",
            temperature=0.1,
            max_tokens=2048,
        ),
        TaskKind.IMAGE_GENERATION: ModelRoute(
            task=TaskKind.IMAGE_GENERATION,
            tier=1,
            provider="local-sd",
            model_id="sd-turbo",
            temperature=0.0,
            max_tokens=None,
        ),
    }

    @classmethod
    def get_route(cls, task: TaskKind) -> ModelRoute:
        """Get model route for a task kind."""
        return cls.DEFAULT_ROUTES[task]
