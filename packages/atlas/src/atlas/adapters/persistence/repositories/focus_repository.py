"""Repository for Focus, Active Focus pointer, Domains, and Entities."""

from atlas.adapters.persistence.tables import (
    ActiveFocusTable,
    DomainTable,
    EntityTable,
    FocusTable,
)
from atlas.domain.focus.models import (
    ActiveFocusPointer,
    Domain,
    Entity,
    Facet,
    Focus,
    ResearchProfile,
    ScopeMode,
)
from atlas.domain.knowledge.models import SourceTier
from atlas.platform.clock import utc_now
from atlas.platform.errors import FocusNotFoundError
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession


class FocusRepository:
    """Data access repository for Focus, Domains, and Entities."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # =========================================================================
    # Domains & Research Profiles
    # =========================================================================

    async def save_domain(self, domain: Domain) -> Domain:
        """Persist or update a Domain definition with its Research Profile."""
        existing = await self.session.get(DomainTable, domain.id)
        if existing:
            existing.name = domain.name
            existing.description = domain.description
            existing.research_profile = domain.research_profile.model_dump(mode="json")
        else:
            row = DomainTable(
                id=domain.id,
                name=domain.name,
                description=domain.description,
                research_profile=domain.research_profile.model_dump(mode="json"),
            )
            self.session.add(row)
        await self.session.flush()
        return domain

    async def get_domain(self, domain_id: str) -> Domain | None:
        """Fetch Domain by ID."""
        row = await self.session.get(DomainTable, domain_id)
        if not row:
            return None
        profile_data = dict(row.research_profile)
        if "source_tier_floor" in profile_data:
            profile_data["source_tier_floor"] = SourceTier(profile_data["source_tier_floor"])
        return Domain(
            id=row.id,
            name=row.name,
            description=row.description,
            research_profile=ResearchProfile(**profile_data),
        )

    # =========================================================================
    # Entities
    # =========================================================================

    async def save_entity(self, entity: Entity) -> Entity:
        """Persist or update an Entity."""
        existing = await self.session.get(EntityTable, entity.id)
        if existing:
            existing.wikidata_qid = entity.wikidata_qid
            existing.name = entity.name
            existing.description = entity.description
            existing.domain_id = entity.domain_id
            existing.aliases = list(entity.aliases)
        else:
            row = EntityTable(
                id=entity.id,
                wikidata_qid=entity.wikidata_qid,
                name=entity.name,
                description=entity.description,
                domain_id=entity.domain_id,
                aliases=list(entity.aliases),
            )
            self.session.add(row)
        await self.session.flush()
        return entity

    async def get_entity(self, entity_id: str) -> Entity | None:
        """Fetch Entity by ID or Wikidata QID."""
        row = await self.session.get(EntityTable, entity_id)
        if not row:
            # Try lookup by wikidata_qid
            stmt = select(EntityTable).where(EntityTable.wikidata_qid == entity_id)
            row = (await self.session.execute(stmt)).scalar_one_or_none()
        if not row:
            return None
        return Entity(
            id=row.id,
            wikidata_qid=row.wikidata_qid,
            name=row.name,
            description=row.description,
            domain_id=row.domain_id,
            aliases=list(row.aliases or []),
        )

    # =========================================================================
    # Focus
    # =========================================================================

    async def save_focus(self, focus: Focus) -> Focus:
        """Persist an immutable Focus record."""
        facets_data = [f.model_dump(mode="json") for f in focus.facets]
        row = FocusTable(
            id=focus.id,
            name=focus.name,
            scope_mode=focus.scope_mode.value,
            facets=facets_data,
            entity_id=focus.entity_id,
            actor_id=focus.actor_id,
            created_at=focus.created_at,
        )
        self.session.add(row)
        await self.session.flush()
        return focus

    async def get_focus(self, focus_id: str) -> Focus:
        """Fetch Focus by ID."""
        row = await self.session.get(FocusTable, focus_id)
        if not row:
            raise FocusNotFoundError(focus_id)
        facets = [Facet(**f) for f in (row.facets or [])]
        return Focus(
            id=row.id,
            name=row.name,
            scope_mode=ScopeMode(row.scope_mode),
            facets=facets,
            entity_id=row.entity_id,
            actor_id=row.actor_id,
            created_at=row.created_at,
        )

    # =========================================================================
    # Active Focus Pointer
    # =========================================================================

    async def set_active_focus(self, focus_id: str, actor_id: str) -> ActiveFocusPointer:
        """Set the active focus pointer for default run initialization."""
        # Ensure focus exists
        await self.get_focus(focus_id)

        await self.session.execute(delete(ActiveFocusTable).where(ActiveFocusTable.id == "default"))
        now = utc_now()
        row = ActiveFocusTable(
            id="default",
            focus_id=focus_id,
            updated_at=now,
            actor_id=actor_id,
        )
        self.session.add(row)
        await self.session.flush()
        return ActiveFocusPointer(focus_id=focus_id, updated_at=now, actor_id=actor_id)

    async def get_active_focus(self) -> ActiveFocusPointer | None:
        """Fetch current active focus pointer."""
        row = await self.session.get(ActiveFocusTable, "default")
        if not row:
            return None
        return ActiveFocusPointer(
            focus_id=row.focus_id,
            updated_at=row.updated_at,
            actor_id=row.actor_id,
        )
