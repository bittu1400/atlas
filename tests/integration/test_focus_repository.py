"""Integration tests for Focus, Domains, Entities, and Active Focus pointer (ADR-0002)."""

from datetime import UTC, datetime

import pytest
from atlas.adapters.persistence.repositories.focus_repository import FocusRepository
from atlas.domain.focus.models import (
    Domain,
    Entity,
    Facet,
    Focus,
    ResearchProfile,
    ScopeMode,
)
from atlas.domain.knowledge.models import SourceTier
from atlas.platform.errors import FocusNotFoundError
from atlas.platform.ids import generate_focus_id
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_focus_and_domain_lifecycle(db_session: AsyncSession) -> None:
    """Test saving and retrieving Domain, Entity, and Focus with facets."""
    repo = FocusRepository(db_session)
    now = datetime(2026, 7, 30, 10, 0, 0, tzinfo=UTC)

    # 1. Create Domain with Research Profile
    domain = Domain(
        id="dom_space",
        name="Space Exploration",
        description="Astronomy, astrophysics, and planetary exploration",
        research_profile=ResearchProfile(
            preferred_apis=["nasa_api", "arxiv", "ads"],
            source_allowlist=["*.nasa.gov", "*.esa.int", "*.nature.com"],
            source_tier_floor=SourceTier.PEER_REVIEWED,
            vocabulary=["orbit", "telemetry", "propulsion", "exoplanet"],
            disambiguation_hints=["celestial body", "spacecraft", "space mission"],
        ),
    )
    await repo.save_domain(domain)

    retrieved_domain = await repo.get_domain("dom_space")
    assert retrieved_domain is not None
    assert retrieved_domain.name == "Space Exploration"
    assert retrieved_domain.research_profile.source_tier_floor == SourceTier.PEER_REVIEWED

    # 2. Create Entity anchored to Wikidata
    entity = Entity(
        id="Q2",
        wikidata_qid="Q2",
        name="Earth",
        description="Third planet from the Sun",
        domain_id="dom_space",
        aliases=["Terra", "The Blue Marble"],
    )
    await repo.save_entity(entity)

    retrieved_entity = await repo.get_entity("Q2")
    assert retrieved_entity is not None
    assert retrieved_entity.name == "Earth"
    assert "The Blue Marble" in retrieved_entity.aliases

    # 3. Create Focus with Facets
    focus_id = generate_focus_id()
    focus = Focus(
        id=focus_id,
        name="Earth Observation Missions",
        scope_mode=ScopeMode.SOFT,
        facets=[
            Facet(dimension="domain", value="dom_space"),
            Facet(dimension="subject", value="Earth"),
            Facet(dimension="era", value="21st century"),
        ],
        entity_id="Q2",
        actor_id="operator_01",
        created_at=now,
    )
    await repo.save_focus(focus)

    retrieved_focus = await repo.get_focus(focus_id)
    assert retrieved_focus.id == focus_id
    assert retrieved_focus.scope_mode == ScopeMode.SOFT
    assert len(retrieved_focus.facets) == 3
    assert retrieved_focus.facets[2].value == "21st century"

    # 4. Set Active Focus Pointer
    active = await repo.set_active_focus(focus_id, actor_id="operator_01")
    assert active.focus_id == focus_id

    current_active = await repo.get_active_focus()
    assert current_active is not None
    assert current_active.focus_id == focus_id


@pytest.mark.asyncio
async def test_raises_on_non_existent_focus(db_session: AsyncSession) -> None:
    """Non-existent Focus lookup raises FocusNotFoundError."""
    repo = FocusRepository(db_session)
    with pytest.raises(FocusNotFoundError):
        await repo.get_focus("foc_non_existent")
