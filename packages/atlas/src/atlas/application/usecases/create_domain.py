"""Create Domain Use Case.

Defect V-15: `FocusRepositoryPort.save_domain` had no production caller, so a
Domain — the row a Topic hangs off — could only be created by a test fixture.
"""

from atlas.application.ports.repositories import FocusRepositoryPort
from atlas.domain.focus.models import Domain, ResearchProfile
from atlas.platform.errors import DuplicateEntityError
from atlas.platform.logging import get_logger

logger = get_logger("usecases.create_domain")


class CreateDomainUseCase:
    """Use case to register a Domain and its Research Profile."""

    def __init__(self, focus_repo: FocusRepositoryPort) -> None:
        self.focus_repo = focus_repo

    async def execute(
        self,
        domain_id: str,
        name: str,
        description: str,
        research_profile: ResearchProfile | None = None,
    ) -> Domain:
        """Register a Domain, defaulting its Research Profile to the empty policy.

        An empty Research Profile is not a permissive one: `ResearchProfile`
        defaults `source_tier_floor` to `INSTITUTIONAL`, so a Domain created
        without one still carries the tier floor rather than none.
        """
        if await self.focus_repo.get_domain(domain_id) is not None:
            raise DuplicateEntityError("Domain", domain_id)

        domain = Domain(
            id=domain_id,
            name=name,
            description=description,
            research_profile=research_profile or ResearchProfile(),
        )
        saved = await self.focus_repo.save_domain(domain)
        logger.info("domain.created", domain_id=saved.id)
        return saved
