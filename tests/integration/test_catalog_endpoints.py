"""The HTTP surface an operator needs before a Run can exist (T-64).

Until these routes existed the dashboard could not name a single Topic,
Channel or Focus, so its Launch form was three free-text boxes over IDs only
the terminal could reveal — and typing one that did not exist was the defect
**V-16** 500 until this morning.

Every assertion here is about rows: what the API lists is what the database
holds, and what it refuses is what the database would have refused later and
less clearly.
"""

import pytest
from atlas.adapters.persistence.repositories.focus_repository import FocusRepository
from atlas.adapters.persistence.repositories.publishing_repository import PublishingRepository
from atlas.adapters.persistence.repositories.source_repository import SourceRepository
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_lists_the_domains_the_migration_seeded(api_client: AsyncClient) -> None:
    """`0001_initial_schema` seeds four Domains; the route returns rows, not a fixture."""
    response = await api_client.get("/domains")

    assert response.status_code == 200
    body = response.json()
    history = next(d for d in body if d["id"] == "dom_history")
    assert history["research_profile"]["source_tier_floor"] == "primary"


@pytest.mark.asyncio
async def test_creates_a_domain_and_then_lists_it(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    payload = {
        "id": "dom_probe",
        "name": "PLACEHOLDER_DOMAIN_NAME",
        "description": "PLACEHOLDER_DOMAIN_DESCRIPTION",
    }
    created = await api_client.post("/domains", json=payload)

    assert created.status_code == 201
    assert created.json()["id"] == "dom_probe"

    listed = await api_client.get("/domains")
    assert "dom_probe" in [d["id"] for d in listed.json()]

    row = await FocusRepository(db_session).get_domain("dom_probe")
    assert row is not None
    assert row.name == "PLACEHOLDER_DOMAIN_NAME"


@pytest.mark.asyncio
async def test_creating_a_domain_that_exists_is_a_conflict_not_an_overwrite(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Defect V-17: `create` used to replace the row, blanking its Research Profile."""
    response = await api_client.post(
        "/domains",
        json={"id": "dom_history", "name": "OTHER", "description": "OTHER"},
    )

    assert response.status_code == 409
    assert response.json()["error"] == "DuplicateEntityError"

    unchanged = await FocusRepository(db_session).get_domain("dom_history")
    assert unchanged is not None
    assert unchanged.research_profile.source_tier_floor.value == "primary"


@pytest.mark.asyncio
async def test_creates_a_topic_and_lists_it_newest_first(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    created = await api_client.post(
        "/topics",
        json={
            "id": "topic_probe",
            "title": "PLACEHOLDER_TOPIC_TITLE",
            "domain_id": "dom_history",
        },
    )

    assert created.status_code == 201
    assert created.json()["status"] == "proposed"

    listed = await api_client.get("/topics")
    assert listed.json()[0]["id"] == "topic_probe"

    row = await SourceRepository(db_session).get_topic("topic_probe")
    assert row is not None
    assert row.domain_id == "dom_history"


@pytest.mark.asyncio
async def test_creating_a_topic_under_an_unknown_domain_is_a_404(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/topics",
        json={"id": "topic_probe", "title": "PLACEHOLDER", "domain_id": "dom_absent"},
    )

    assert response.status_code == 404
    assert response.json()["error"] == "DomainNotFoundError"


@pytest.mark.asyncio
async def test_creates_a_channel_and_lists_it(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    created = await api_client.post(
        "/channels",
        json={
            "id": "channel_probe",
            "name": "PLACEHOLDER_CHANNEL_NAME",
            "audience_timezone": "UTC",
        },
    )

    assert created.status_code == 201

    listed = await api_client.get("/channels")
    ids = [c["id"] for c in listed.json()]
    assert "channel_probe" in ids
    assert "origins" in ids, "the seeded Channels are listed too"

    row = await PublishingRepository(db_session).get_channel("channel_probe")
    assert row is not None
    assert row.audience_timezone == "UTC"


@pytest.mark.asyncio
async def test_creates_a_focus_and_marks_the_active_one_in_the_listing(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """A Run without an explicit Focus captures the active one by value (Invariant 6).

    A picker that cannot say which Focus is active hides the default it is
    about to apply, so the listing resolves the pointer even though the
    repository does not.
    """
    created = await api_client.post(
        "/focuses",
        json={
            "name": "PLACEHOLDER_FOCUS_NAME",
            "scope_mode": "soft",
            "facets": [{"dimension": "domain", "value": "dom_history"}],
            "actor_id": "operator_probe",
        },
    )

    assert created.status_code == 201
    focus_id = created.json()["id"]
    assert focus_id.startswith("foc_")

    listed = await api_client.get("/focuses")
    assert listed.status_code == 200
    entry = next(f for f in listed.json() if f["id"] == focus_id)
    assert entry["is_active"] is False, "creating a Focus does not make it the default"

    await FocusRepository(db_session).set_active_focus(focus_id, actor_id="operator_probe")
    after = await api_client.get("/focuses")
    assert [f["id"] for f in after.json() if f["is_active"]] == [focus_id]


@pytest.mark.asyncio
async def test_a_run_can_be_created_from_the_ids_the_listings_returned(
    api_client: AsyncClient,
) -> None:
    """The point of the whole surface: no ID in this test was typed from memory."""
    await api_client.post(
        "/topics",
        json={"id": "topic_probe", "title": "PLACEHOLDER_TOPIC_TITLE", "domain_id": "dom_history"},
    )

    topic_id = (await api_client.get("/topics")).json()[0]["id"]
    channel_id = next(c["id"] for c in (await api_client.get("/channels")).json())

    run = await api_client.post(
        "/runs",
        json={"topic_id": topic_id, "channel_id": channel_id, "actor_id": "operator_probe"},
    )

    assert run.status_code == 201
    assert run.json()["topic_id"] == topic_id
