"""Create Run Use Case.

As specified in SPEC §5, Invariant 10, and ADR-0002:
- Focus is captured by value at Run creation and never re-read from mutable settings.
- Run starts in PENDING status and is transactionally enqueued.
"""

from atlas.application.ports.queue import QueueBroker
from atlas.application.ports.repositories import ExecutionRepositoryPort, FocusRepositoryPort
from atlas.domain.execution.models import Run, RunStatus
from atlas.domain.focus.models import Focus, FocusSnapshot, ScopeMode
from atlas.platform.clock import utc_now
from atlas.platform.ids import generate_id, generate_trace_id
from atlas.platform.logging import get_logger

logger = get_logger("usecases.create_run")


class CreateRunUseCase:
    """Use case to initialize and dispatch a new pipeline Run."""

    def __init__(
        self,
        execution_repo: ExecutionRepositoryPort,
        focus_repo: FocusRepositoryPort,
        queue_broker: QueueBroker,
    ) -> None:
        self.execution_repo = execution_repo
        self.focus_repo = focus_repo
        self.queue_broker = queue_broker

    async def execute(
        self,
        topic_id: str,
        channel_id: str = "origins",
        actor_id: str = "operator",
        focus_id: str | None = None,
    ) -> Run:
        """Create a new Run, capturing Focus by value."""
        # 1. Resolve Focus to capture by value
        focus: Focus | None = None
        if focus_id:
            focus = await self.focus_repo.get_focus(focus_id)
        else:
            active_ptr = await self.focus_repo.get_active_focus()
            if active_ptr:
                focus = await self.focus_repo.get_focus(active_ptr.focus_id)

        if not focus:
            # Fallback default focus if no active focus exists
            focus = Focus(
                id=generate_id("foc"),
                name="Default Focus",
                scope_mode=ScopeMode.SOFT,
                facets=[],
                entity_id=None,
                actor_id=actor_id,
                created_at=utc_now(),
            )

        focus_snapshot = FocusSnapshot.from_focus(focus)

        now = utc_now()
        run = Run(
            id=generate_id("run"),
            topic_id=topic_id,
            channel_id=channel_id,
            status=RunStatus.PENDING,
            captured_focus=focus_snapshot,
            trace_id=generate_trace_id(),
            actor_id=actor_id,
            created_at=now,
            updated_at=now,
        )

        created_run = await self.execution_repo.create_run(run)
        logger.info("run.created", run_id=created_run.id, topic_id=topic_id, channel_id=channel_id)

        # 2. Transactionally enqueue first step
        await self.queue_broker.enqueue(created_run.id)
        return created_run
