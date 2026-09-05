"""Create Focus Use Case.

Defect V-15's shape once more: `FocusRepositoryPort.save_focus` had no
production caller, so the Focus a Run captures by value could only come from a
test fixture or the fallback default `CreateRunUseCase` builds in memory.
"""

from atlas.application.ports.repositories import FocusRepositoryPort
from atlas.domain.focus.models import Facet, Focus, ScopeMode
from atlas.platform.clock import utc_now
from atlas.platform.ids import generate_id
from atlas.platform.logging import get_logger

logger = get_logger("usecases.create_focus")


class CreateFocusUseCase:
    """Use case to register a Focus: a named set of Facets plus a Scope Mode."""

    def __init__(self, focus_repo: FocusRepositoryPort) -> None:
        self.focus_repo = focus_repo

    async def execute(
        self,
        name: str,
        facets: list[Facet],
        scope_mode: ScopeMode = ScopeMode.SOFT,
        entity_id: str | None = None,
        actor_id: str = "operator",
    ) -> Focus:
        """Register a Focus under a generated ID.

        The ID is generated rather than supplied, which is why this use case
        needs no duplicate check: a Focus is immutable and versioned by
        creation, so two Focuses with the same Facets are two rows, not a
        conflict. Creating one does **not** make it the Active Focus — that
        pointer is a separate, deliberate act.
        """
        focus = Focus(
            id=generate_id("foc"),
            name=name,
            scope_mode=scope_mode,
            facets=facets,
            entity_id=entity_id,
            actor_id=actor_id,
            created_at=utc_now(),
        )
        saved = await self.focus_repo.save_focus(focus)
        logger.info("focus.created", focus_id=saved.id, scope_mode=scope_mode.value)
        return saved
