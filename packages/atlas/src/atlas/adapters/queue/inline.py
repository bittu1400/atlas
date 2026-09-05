"""The dispatch Atlas actually performs today: none.

**This is not the queue ADR-0001 describes, and it does not pretend to be.**
That ADR decides Postgres is the queue, that Dramatiq workers execute Steps,
and that "the API only validates and enqueues; it never executes pipeline
work". None of the three is built:

- there is no Postgres broker, and dramatiq's default is Redis, which ADR-0001
  rejected by name and which is neither a dependency nor a Compose service
  (defect **V-18**);
- `POST /runs` and `atlas run create` both call `run_pipeline` inline, so the
  API does execute pipeline work inside the request (defect **V-19**);
- and because they *also* enqueued, a working broker would have made every Run
  execute twice.

Naming this `InlineQueueBroker` rather than leaving `DramatiqQueueBroker`
wired is rule **R3**: a component that queues nothing must not wear a queue's
name, and `docs/STATUS.md` §3 must say the background queue does not exist.
"""

from typing import Any

from atlas.application.ports.queue import QueueBroker
from atlas.platform.logging import get_logger

logger = get_logger("adapters.queue.inline")


class InlineQueueBroker(QueueBroker):
    """Records the dispatch and returns; the caller executes the Run in-process."""

    async def enqueue(self, run_id: str, step_name: str | None = None, **kwargs: Any) -> None:
        """Emit the event and do nothing else.

        A silent no-op would be indistinguishable from a working queue in the
        logs, which is how a Run that never executed would look like one that
        was scheduled. The event name says which of the two happened.
        """
        _ = kwargs
        logger.info(
            "queue.inline_dispatch",
            run_id=run_id,
            step_name=step_name,
            detail="no background queue exists; the caller executes this Run in-process",
        )
