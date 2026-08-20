"""Port interface for Notifications and Operator Alerts."""

from typing import Any, Protocol


class Notifier(Protocol):
    """Port for notifying operators of gate suspensions, quality failures, or completion."""

    async def notify(
        self,
        event: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Send notification to operator channel."""
        ...
