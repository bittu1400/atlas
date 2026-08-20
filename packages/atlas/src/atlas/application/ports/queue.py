"""Port interface for Background Job Queue and Dispatch."""

from typing import Any, Protocol


class QueueBroker(Protocol):
    """Port for transactional step enqueue and background worker dispatch."""

    async def enqueue(self, run_id: str, step_name: str | None = None, **kwargs: Any) -> None:
        """Enqueue pipeline execution task."""
        ...
