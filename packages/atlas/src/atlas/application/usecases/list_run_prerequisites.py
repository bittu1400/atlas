"""Read use cases for the rows a Run needs before it can exist (T-64).

Domains, Topics and Channels are returned as their domain models. A Focus is
not: whether a Focus is *active* lives in a separate pointer row, and joining
the two is composition — which belongs here rather than in the repository,
and rather than in the route.
"""

from atlas.application.ports.repositories import (
    FocusRepositoryPort,
    PublishingRepositoryPort,
    SourceRepositoryPort,
)
from atlas.domain.focus.models import Domain, Facet, Focus, ScopeMode
from atlas.domain.knowledge.models import Topic
from atlas.domain.publishing.models import Channel
from pydantic import BaseModel, ConfigDict, Field


class FocusListing(BaseModel):
    """A Focus plus whether it is the Active Focus.

    A Run created without an explicit Focus captures the active one by value
    (Invariant 6), so a picker that cannot show which one that is hides the
    default it is about to apply.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Focus ID")
    name: str = Field(description="Operator-facing Focus name")
    scope_mode: ScopeMode = Field(description="hard, soft or exploratory")
    facets: list[Facet] = Field(description="The typed constraints this Focus carries")
    entity_id: str | None = Field(default=None, description="Resolved Entity, if any")
    is_active: bool = Field(description="Whether the Active Focus pointer names this Focus")

    @classmethod
    def from_focus(cls, focus: Focus, *, is_active: bool) -> "FocusListing":
        return cls(
            id=focus.id,
            name=focus.name,
            scope_mode=focus.scope_mode,
            facets=list(focus.facets),
            entity_id=focus.entity_id,
            is_active=is_active,
        )


class ListDomainsUseCase:
    """List every Domain an operator can attach a Topic to."""

    def __init__(self, focus_repo: FocusRepositoryPort) -> None:
        self.focus_repo = focus_repo

    async def execute(self) -> list[Domain]:
        return await self.focus_repo.list_domains()


class ListTopicsUseCase:
    """List every Topic an operator can launch a Run against."""

    def __init__(self, source_repo: SourceRepositoryPort) -> None:
        self.source_repo = source_repo

    async def execute(self) -> list[Topic]:
        return await self.source_repo.list_topics()


class ListChannelsUseCase:
    """List every Channel a Run can publish to."""

    def __init__(self, publishing_repo: PublishingRepositoryPort) -> None:
        self.publishing_repo = publishing_repo

    async def execute(self) -> list[Channel]:
        return await self.publishing_repo.list_channels()


class ListFocusesUseCase:
    """List every Focus, resolving the Active Focus pointer against the list."""

    def __init__(self, focus_repo: FocusRepositoryPort) -> None:
        self.focus_repo = focus_repo

    async def execute(self) -> list[FocusListing]:
        focuses = await self.focus_repo.list_focuses()
        pointer = await self.focus_repo.get_active_focus()
        active_id = pointer.focus_id if pointer else None
        return [FocusListing.from_focus(f, is_active=f.id == active_id) for f in focuses]
