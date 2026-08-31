"""Structured-log notifier.

The operator dashboard reads gate state from the database, so notification has
no second delivery channel yet. This adapter is not a stand-in for one: it does
exactly what it says, writes the event to the structured log, and makes no
claim about reaching a human. A push/e-mail adapter would be a new adapter, not
a change to this one.
"""

from typing import Any

from atlas.application.ports.notify import Notifier
from atlas.platform.logging import get_logger

logger = get_logger("adapters.notify")


class LoggingNotifier(Notifier):
    """Emits operator notifications to the structured log."""

    async def notify(
        self,
        event: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Write one structured log line per operator notification."""
        logger.info("notify.emitted", event=event, message=message, **(payload or {}))
