"""Defect V-18: the queue broker the production container wires could not run.

`Container.queue_broker` was `DramatiqQueueBroker`, whose `enqueue` imports
`apps.worker.tasks`, whose `@dramatiq.actor` decorator calls `get_broker()`.
No broker is configured anywhere in production, so dramatiq fell back to its
own default — `RedisBroker` — and `redis` is neither a dependency in
`pyproject.toml` nor a service in `docker-compose.yml`. Every `POST /runs` and
every `atlas run create` died with `ModuleNotFoundError: No module named
'redis'` after the Run row had already been built.

Nothing caught it because nothing ever called it: `tests/conftest.py` sets a
global `StubBroker` for the whole session, and the API tests override
`get_queue_broker` with `FakeQueueBroker`. That is defect **V-07**'s shape a
second time — the production adapter that no test touches.

This test calls the broker the production container actually resolves.
"""

import pytest
from atlas.adapters.container import Container
from atlas.adapters.queue.inline import InlineQueueBroker


@pytest.mark.asyncio
async def test_the_container_resolves_a_queue_broker_that_can_be_called() -> None:
    """The whole defect in one line: this raised `ModuleNotFoundError`."""
    broker = Container().queue_broker

    await broker.enqueue("run_probe")


def test_the_default_broker_does_not_pretend_to_have_queued_anything() -> None:
    """Rule R3: a component that queues nothing must not wear a queue's name.

    ADR-0001 says Postgres is the queue and that the API only enqueues, never
    executes. Neither is built: there is no Postgres broker, and both entry
    points run the pipeline in-process. `InlineQueueBroker` is named for what
    actually happens, and `docs/STATUS.md` §3 says the background queue does
    not exist.
    """
    broker = Container().queue_broker

    assert isinstance(broker, InlineQueueBroker)
    assert type(broker).__name__ != "DramatiqQueueBroker"


@pytest.mark.asyncio
async def test_the_dramatiq_broker_is_still_selectable_by_configuration() -> None:
    """The real broker is configuration away, not deleted — it needs a running one."""
    from atlas.adapters.queue.dramatiq_broker import DramatiqQueueBroker

    broker = Container(queue_broker_kind="dramatiq").queue_broker

    assert isinstance(broker, DramatiqQueueBroker)
