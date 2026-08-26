import asyncio
from typing import Any

from atlas.application.ports.queue import QueueBroker


class DramatiqQueueBroker(QueueBroker):
    """Real queue broker using Dramatiq for background jobs."""

    async def enqueue(self, run_id: str, step_name: str | None = None, **kwargs: Any) -> None:
        from apps.worker.tasks import execute_pipeline_task

        loop = asyncio.get_running_loop()
        # dramatiq .send is synchronous, so we run it in an executor
        await loop.run_in_executor(None, lambda: execute_pipeline_task.send(run_id=run_id))
