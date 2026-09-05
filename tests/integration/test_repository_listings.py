"""Listing the rows an operator has to choose from (T-64).

Every repository could fetch one row by ID and none could enumerate, so the
dashboard had nothing to populate a picker with and the Launch form stayed a
free-text box over IDs only the terminal could reveal. These four methods are
the read half of that gap; the routes over them are the other half.

Ordering is asserted, not incidental: a picker whose options move between
renders is worse than one that is merely long.

These tests do not assume an empty table. Migration `0001_initial_schema`
seeds four Domains and three Channels, so a listing is asserted by where the
new rows land relative to each other, never by the whole list being equal to
what this test inserted.
"""

from datetime import timedelta

import pytest
from atlas.adapters.persistence.repositories.focus_repository import FocusRepository
from atlas.adapters.persistence.repositories.publishing_repository import PublishingRepository
from atlas.adapters.persistence.repositories.source_repository import SourceRepository
from atlas.application.usecases.create_channel import CreateChannelUseCase
from atlas.application.usecases.create_domain import CreateDomainUseCase
from atlas.application.usecases.create_topic import CreateTopicUseCase
from atlas.domain.focus.models import Facet, Focus, ScopeMode
from atlas.platform.clock import utc_now
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_lists_every_domain_by_name(db_session: AsyncSession) -> None:
    focus_repo = FocusRepository(db_session)
    use_case = CreateDomainUseCase(focus_repo)
    await use_case.execute(
        domain_id="dom_probe_b", name="PLACEHOLDER_NAME_B", description="PLACEHOLDER_DESC_B"
    )
    await use_case.execute(
        domain_id="dom_probe_a", name="PLACEHOLDER_NAME_A", description="PLACEHOLDER_DESC_A"
    )

    domains = await focus_repo.list_domains()

    ids = [d.id for d in domains]
    assert ids == sorted(ids)
    assert ids.index("dom_probe_a") < ids.index("dom_probe_b")
    # The seeded Domains are listed too, with their Research Profile intact.
    seeded = next(d for d in domains if d.id == "dom_history")
    assert seeded.research_profile.source_tier_floor.value == "primary"


@pytest.mark.asyncio
async def test_lists_every_topic_newest_first(db_session: AsyncSession) -> None:
    """Newest first: the Topic an operator just created is the one they want to launch."""
    focus_repo = FocusRepository(db_session)
    source_repo = SourceRepository(db_session)
    await CreateDomainUseCase(focus_repo).execute(
        domain_id="dom_probe", name="PLACEHOLDER_NAME", description="PLACEHOLDER_DESC"
    )
    use_case = CreateTopicUseCase(source_repo, focus_repo)
    await use_case.execute(
        topic_id="topic_probe_older", title="PLACEHOLDER_TITLE_OLDER", domain_id="dom_probe"
    )
    await use_case.execute(
        topic_id="topic_probe_newer", title="PLACEHOLDER_TITLE_NEWER", domain_id="dom_probe"
    )

    topics = await source_repo.list_topics()

    ids = [t.id for t in topics]
    assert ids.index("topic_probe_newer") < ids.index("topic_probe_older")
    assert topics[0].title == "PLACEHOLDER_TITLE_NEWER"


@pytest.mark.asyncio
async def test_lists_every_channel_by_id(db_session: AsyncSession) -> None:
    publishing_repo = PublishingRepository(db_session)
    use_case = CreateChannelUseCase(publishing_repo)
    await use_case.execute(channel_id="channel_probe_b", name="PLACEHOLDER_NAME_B")
    await use_case.execute(
        channel_id="channel_probe_a", name="PLACEHOLDER_NAME_A", style_profile={"tone": "archival"}
    )

    channels = await publishing_repo.list_channels()

    ids = [c.id for c in channels]
    assert ids == sorted(ids)
    assert ids.index("channel_probe_a") < ids.index("channel_probe_b")
    created = next(c for c in channels if c.id == "channel_probe_a")
    assert created.style_profile == {"tone": "archival"}


@pytest.mark.asyncio
async def test_lists_every_focus_newest_first(db_session: AsyncSession) -> None:
    """The repository lists; it does not resolve the Active Focus pointer.

    A Run created without an explicit Focus captures the active one by value
    (Invariant 6), so a picker has to say which Focus is active — but joining
    the pointer to the list is composition, and composition belongs in the use
    case above this, not in the repository.
    """
    focus_repo = FocusRepository(db_session)
    # Explicit timestamps: two utc_now() calls can land close enough that the
    # assertion below would be testing the tiebreaker rather than the ordering.
    created = utc_now()
    for offset, focus_id in ((0, "foc_probe_one"), (60, "foc_probe_two")):
        await focus_repo.save_focus(
            Focus(
                id=focus_id,
                name=f"PLACEHOLDER_FOCUS_{focus_id}",
                scope_mode=ScopeMode.SOFT,
                facets=[Facet(dimension="domain", value="dom_probe")],
                entity_id=None,
                actor_id="operator_probe",
                created_at=created + timedelta(seconds=offset),
            )
        )
    await focus_repo.set_active_focus("foc_probe_two", actor_id="operator_probe")

    focuses = await focus_repo.list_focuses()

    ids = [f.id for f in focuses]
    assert ids.index("foc_probe_two") < ids.index("foc_probe_one")
    assert focuses[0].scope_mode == ScopeMode.SOFT
    assert [f.dimension for f in focuses[0].facets] == ["domain"]
