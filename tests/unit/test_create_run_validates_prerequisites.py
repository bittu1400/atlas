"""Defect V-16: `CreateRunUseCase` validated nothing before flushing the Run.

The Topic and Channel foreign keys were the only check, so an unknown
`topic_id` surfaced as SQLAlchemy's `IntegrityError` — an infrastructure
exception no handler types — and reached the API's catch-all as a 500. Both
entry points, `POST /runs` and `atlas run create`, route through this use case,
so the guard belongs here rather than in either caller.
"""

import pytest
from atlas.application.usecases.create_run import CreateRunUseCase
from atlas.domain.execution.models import Run, RunStatus
from atlas.domain.focus.models import ActiveFocusPointer, Domain, Focus
from atlas.domain.knowledge.models import Topic, TopicStatus
from atlas.domain.publishing.models import Channel
from atlas.platform.clock import utc_now
from atlas.platform.errors import ChannelNotFoundError, TopicNotFoundError

TOPIC_ID = "topic_probe"
CHANNEL_ID = "channel_probe"


class _StubExecutionRepo:
    """Records the Run it is handed; the real one would flush it."""

    def __init__(self) -> None:
        self.created: Run | None = None

    async def create_run(self, run: Run) -> Run:
        self.created = run
        return run


class _StubFocusRepo:
    """No active Focus, so the use case falls back to its default Focus."""

    async def get_focus(self, focus_id: str) -> Focus | None:  # noqa: ARG002
        return None

    async def get_active_focus(self) -> ActiveFocusPointer | None:
        return None

    async def save_domain(self, domain: Domain) -> Domain:
        return domain


class _StubSourceRepo:
    def __init__(self, topics: dict[str, Topic]) -> None:
        self.topics = topics

    async def get_topic(self, topic_id: str) -> Topic | None:
        return self.topics.get(topic_id)


class _StubPublishingRepo:
    def __init__(self, channels: dict[str, Channel]) -> None:
        self.channels = channels

    async def get_channel(self, channel_id: str) -> Channel | None:
        return self.channels.get(channel_id)


class _StubQueueBroker:
    def __init__(self) -> None:
        self.enqueued: list[str] = []

    async def enqueue(self, run_id: str) -> None:
        self.enqueued.append(run_id)


def _topic() -> Topic:
    return Topic(
        id=TOPIC_ID,
        title="PLACEHOLDER_TOPIC_TITLE",
        domain_id="dom_probe",
        status=TopicStatus.PROPOSED,
        created_at=utc_now(),
    )


def _channel() -> Channel:
    return Channel(
        id=CHANNEL_ID,
        name="PLACEHOLDER_CHANNEL_NAME",
        audience_timezone="UTC",
        style_profile={},
        created_at=utc_now(),
    )


def _use_case(
    *,
    topics: dict[str, Topic] | None = None,
    channels: dict[str, Channel] | None = None,
) -> tuple[CreateRunUseCase, _StubExecutionRepo, _StubQueueBroker]:
    execution_repo = _StubExecutionRepo()
    queue_broker = _StubQueueBroker()
    use_case = CreateRunUseCase(
        execution_repo,  # type: ignore[arg-type]
        _StubFocusRepo(),  # type: ignore[arg-type]
        queue_broker,  # type: ignore[arg-type]
        _StubSourceRepo(topics if topics is not None else {TOPIC_ID: _topic()}),  # type: ignore[arg-type]
        _StubPublishingRepo(  # type: ignore[arg-type]
            channels if channels is not None else {CHANNEL_ID: _channel()}
        ),
    )
    return use_case, execution_repo, queue_broker


@pytest.mark.asyncio
async def test_rejects_a_run_for_a_topic_that_does_not_exist() -> None:
    use_case, execution_repo, queue_broker = _use_case(topics={})

    with pytest.raises(TopicNotFoundError) as excinfo:
        await use_case.execute(topic_id=TOPIC_ID, channel_id=CHANNEL_ID)

    assert excinfo.value.topic_id == TOPIC_ID
    assert TOPIC_ID in str(excinfo.value)
    assert execution_repo.created is None, "the Run must not reach the repository"
    assert queue_broker.enqueued == []


@pytest.mark.asyncio
async def test_rejects_a_run_for_a_channel_that_does_not_exist() -> None:
    """`channel_id` defaults to 'origins', so the same 500 is one bad default away."""
    use_case, execution_repo, queue_broker = _use_case(channels={})

    with pytest.raises(ChannelNotFoundError) as excinfo:
        await use_case.execute(topic_id=TOPIC_ID, channel_id=CHANNEL_ID)

    assert excinfo.value.channel_id == CHANNEL_ID
    assert execution_repo.created is None
    assert queue_broker.enqueued == []


@pytest.mark.asyncio
async def test_creates_the_run_when_both_rows_exist() -> None:
    use_case, execution_repo, queue_broker = _use_case()

    run = await use_case.execute(topic_id=TOPIC_ID, channel_id=CHANNEL_ID)

    assert run.status == RunStatus.PENDING
    assert run.topic_id == TOPIC_ID
    assert execution_repo.created is run
    assert queue_broker.enqueued == [run.id]
