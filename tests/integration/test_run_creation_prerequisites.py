"""Defect V-15: nothing outside `tests/` could create the rows a Run needs.

`save_domain`, `save_topic` and `save_channel` each had zero production
callers, so `topics` was empty in any database a test had not seeded and
`POST /runs` violated `runs_topic_id_fkey` for every input. This drives the
sequence an operator now has — Domain, then Topic, then Channel, then Run —
against the real schema, and asserts the rows rather than the return values.
"""

import pytest
from atlas.adapters.fakes.providers import FakeQueueBroker
from atlas.adapters.persistence.repositories.execution_repository import ExecutionRepository
from atlas.adapters.persistence.repositories.focus_repository import FocusRepository
from atlas.adapters.persistence.repositories.publishing_repository import PublishingRepository
from atlas.adapters.persistence.repositories.source_repository import SourceRepository
from atlas.application.usecases.create_channel import CreateChannelUseCase
from atlas.application.usecases.create_domain import CreateDomainUseCase
from atlas.application.usecases.create_run import CreateRunUseCase
from atlas.application.usecases.create_topic import CreateTopicUseCase
from atlas.domain.execution.models import RunStatus
from atlas.domain.knowledge.models import TopicStatus
from atlas.platform.errors import DomainNotFoundError, TopicNotFoundError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

DOMAIN_ID = "dom_probe"
TOPIC_ID = "topic_probe"
CHANNEL_ID = "channel_probe"


@pytest.mark.asyncio
async def test_an_operator_can_reach_a_run_from_an_empty_database(
    db_session: AsyncSession,
) -> None:
    """The whole point of T-62: no test fixture in the chain, only shipped use cases."""
    source_repo = SourceRepository(db_session)
    focus_repo = FocusRepository(db_session)
    publishing_repo = PublishingRepository(db_session)

    domain = await CreateDomainUseCase(focus_repo).execute(
        domain_id=DOMAIN_ID,
        name="PLACEHOLDER_DOMAIN_NAME",
        description="PLACEHOLDER_DOMAIN_DESCRIPTION",
    )
    topic = await CreateTopicUseCase(source_repo, focus_repo).execute(
        topic_id=TOPIC_ID,
        title="PLACEHOLDER_TOPIC_TITLE",
        domain_id=DOMAIN_ID,
    )
    channel = await CreateChannelUseCase(publishing_repo).execute(
        channel_id=CHANNEL_ID,
        name="PLACEHOLDER_CHANNEL_NAME",
        audience_timezone="UTC",
    )

    assert domain.id == DOMAIN_ID
    assert topic.status == TopicStatus.PROPOSED
    assert channel.audience_timezone == "UTC"

    run = await CreateRunUseCase(
        ExecutionRepository(db_session),
        focus_repo,
        FakeQueueBroker(),
        source_repo,
        publishing_repo,
    ).execute(topic_id=TOPIC_ID, channel_id=CHANNEL_ID, actor_id="operator_probe")

    assert run.status == RunStatus.PENDING

    rows = (
        await db_session.execute(
            text(
                "SELECT (SELECT count(*) FROM domains WHERE id = :d),"
                "       (SELECT count(*) FROM topics WHERE id = :t),"
                "       (SELECT count(*) FROM channels WHERE id = :c),"
                "       (SELECT count(*) FROM runs WHERE id = :r)"
            ),
            {"d": DOMAIN_ID, "t": TOPIC_ID, "c": CHANNEL_ID, "r": run.id},
        )
    ).one()
    assert tuple(rows) == (1, 1, 1, 1)


@pytest.mark.asyncio
async def test_a_topic_cannot_be_created_for_a_domain_that_does_not_exist(
    db_session: AsyncSession,
) -> None:
    """The same foreign key one level up: fail with a reason, not an IntegrityError."""
    use_case = CreateTopicUseCase(SourceRepository(db_session), FocusRepository(db_session))

    with pytest.raises(DomainNotFoundError) as excinfo:
        await use_case.execute(
            topic_id=TOPIC_ID, title="PLACEHOLDER_TOPIC_TITLE", domain_id="dom_absent"
        )

    assert excinfo.value.domain_id == "dom_absent"
    count = (
        await db_session.execute(text("SELECT count(*) FROM topics WHERE id = :t"), {"t": TOPIC_ID})
    ).scalar_one()
    assert count == 0


@pytest.mark.asyncio
async def test_creating_a_run_for_an_unknown_topic_raises_before_the_flush(
    db_session: AsyncSession,
) -> None:
    """V-16 against the real session: no IntegrityError, and no half-written row."""
    use_case = CreateRunUseCase(
        ExecutionRepository(db_session),
        FocusRepository(db_session),
        FakeQueueBroker(),
        SourceRepository(db_session),
        PublishingRepository(db_session),
    )

    with pytest.raises(TopicNotFoundError):
        await use_case.execute(topic_id="topic_absent", channel_id=CHANNEL_ID)

    count = (await db_session.execute(text("SELECT count(*) FROM runs"))).scalar_one()
    assert count == 0
