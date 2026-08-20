"""Domain models for Focus, Facets, Scope Modes, and Entity bindings.

As specified in ADR-0002:
- Focus is a first-class versioned entity, capturing facets (dimension, value).
- Runs capture Focus by value at creation.
- Active Focus pointer supplies default for newly created Runs.
- Field maps to a Domain with a Research Profile; Note resolves to an Entity.
"""

from datetime import datetime
from enum import StrEnum

from atlas.domain.common.enums import SourceTier
from pydantic import BaseModel, ConfigDict, Field


class ScopeMode(StrEnum):
    """Scoping mode defining research boundaries."""

    HARD = "hard"  # Never leave the Focus
    SOFT = "soft"  # Prefer the Focus, allow adjacent graph nodes (default)
    EXPLORATORY = "exploratory"  # Focus as seed


class Facet(BaseModel):
    """Typed (dimension, value) constraint inside a Focus."""

    model_config = ConfigDict(frozen=True)

    dimension: str = Field(description="Dimension name (e.g. domain, subject, era, region)")
    value: str = Field(description="Dimension value")


class ResearchProfile(BaseModel):
    """Policy attached to a Domain defining source allowlists and preferred APIs."""

    model_config = ConfigDict(frozen=True)

    preferred_apis: list[str] = Field(
        default_factory=list, description="Preferred search and database APIs"
    )
    source_allowlist: list[str] = Field(
        default_factory=list, description="Domain allowlist patterns"
    )
    source_tier_floor: SourceTier = Field(
        default=SourceTier.INSTITUTIONAL, description="Minimum acceptable source tier"
    )
    vocabulary: list[str] = Field(default_factory=list, description="Query expansion vocabulary")
    disambiguation_hints: list[str] = Field(
        default_factory=list, description="Hints for resolving entities"
    )


class Domain(BaseModel):
    """Named area of knowledge carrying a Research Profile."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Unique Domain ID (e.g. dom_animal, dom_history)")
    name: str = Field(description="Domain name (e.g. Animal, History, Technology)")
    description: str = Field(description="Description of domain coverage")
    research_profile: ResearchProfile = Field(description="Domain research policy")


class Entity(BaseModel):
    """Canonical externally-anchored entity (e.g. Wikidata QID)."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Entity ID or QID (e.g. Q19939)")
    wikidata_qid: str | None = Field(default=None, pattern=r"^Q\d+$", description="Wikidata QID")
    name: str = Field(description="Primary label / name")
    description: str | None = Field(default=None, description="Entity disambiguation description")
    domain_id: str = Field(description="Associated Domain ID")
    aliases: list[str] = Field(default_factory=list, description="Alternative names / aliases")


class Focus(BaseModel):
    """Immutable Focus configuration captured by value into Runs."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Unique Focus ID")
    name: str = Field(description="Human-readable focus name")
    scope_mode: ScopeMode = Field(default=ScopeMode.SOFT, description="Scoping mode")
    facets: list[Facet] = Field(default_factory=list, description="List of constraints")
    entity_id: str | None = Field(default=None, description="Anchored Entity ID")
    actor_id: str = Field(description="Actor ID who created this focus")
    created_at: datetime = Field(description="Creation timestamp in UTC")


class FocusSnapshot(BaseModel):
    """Captured by-value snapshot of a Focus embedded directly in a Run."""

    model_config = ConfigDict(frozen=True)

    focus_id: str = Field(description="Source Focus ID")
    scope_mode: ScopeMode = Field(description="Scope mode at capture time")
    facets: list[Facet] = Field(description="Facets captured at Run creation")
    entity_id: str | None = Field(default=None, description="Entity ID at capture time")
    captured_at: datetime = Field(description="Capture timestamp in UTC")

    @classmethod
    def from_focus(cls, focus: Focus) -> "FocusSnapshot":
        """Capture an immutable snapshot from an active Focus."""
        from atlas.platform.clock import utc_now

        return cls(
            focus_id=focus.id,
            scope_mode=focus.scope_mode,
            facets=list(focus.facets),
            entity_id=focus.entity_id,
            captured_at=utc_now(),
        )


class ActiveFocusPointer(BaseModel):
    """Pointer identifying the default Focus for newly created Runs."""

    model_config = ConfigDict(frozen=True)

    focus_id: str = Field(description="Active Focus ID")
    updated_at: datetime = Field(description="Last update timestamp in UTC")
    actor_id: str = Field(description="Actor ID who updated the active focus")
