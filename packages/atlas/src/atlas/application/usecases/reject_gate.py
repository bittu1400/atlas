"""Reject Gate Use Case.

As specified in SPEC §7 and ADR-0001:
- Rejection MUST carry structured feedback (target_ref, rubric_dimension, reason, action).
- Routes to REGENERATE (reworking), BRANCH (branching), or ABANDON (terminal).
"""

from atlas.application.ports.queue import QueueBroker
from atlas.application.ports.repositories import ExecutionRepositoryPort
from atlas.domain.execution.models import (
    Approval,
    ApprovalDecision,
    Gate,
    GateStatus,
    RejectionAction,
    RejectionFeedback,
    RunStatus,
)
from atlas.platform.clock import utc_now
from atlas.platform.errors import GateAlreadyResolvedError, GateNotFoundError
from atlas.platform.ids import generate_approval_id
from atlas.platform.logging import get_logger

logger = get_logger("usecases.reject_gate")


class RejectGateUseCase:
    """Use case to reject a Gate with structured feedback and trigger rework or abandonment."""

    def __init__(
        self,
        execution_repo: ExecutionRepositoryPort,
        queue_broker: QueueBroker,
    ) -> None:
        self.execution_repo = execution_repo
        self.queue_broker = queue_broker

    async def execute(
        self,
        gate_id: str,
        feedback: RejectionFeedback,
        actor_id: str = "operator",
    ) -> tuple[Gate, Approval]:
        """Reject a pending Gate with structured feedback."""
        gate = await self.execution_repo.get_gate(gate_id)
        if not gate:
            raise GateNotFoundError(gate_id)
        if gate.status != GateStatus.PENDING:
            raise GateAlreadyResolvedError(gate_id, gate.status.value)

        now = utc_now()
        approval = Approval(
            id=generate_approval_id(),
            gate_id=gate.id,
            run_id=gate.run_id,
            actor_id=actor_id,
            decision=ApprovalDecision.REJECTED,
            feedback=feedback,
            created_at=now,
        )

        recorded_approval = await self.execution_repo.record_approval(approval)
        updated_gate = Gate(
            id=gate.id,
            run_id=gate.run_id,
            step_id=gate.step_id,
            gate_type=gate.gate_type,
            status=GateStatus.REJECTED,
            requested_at=gate.requested_at,
            resolved_at=now,
        )

        if feedback.action == RejectionAction.ABANDON:
            await self.execution_repo.update_run_status(
                gate.run_id, RunStatus.ABANDONED, completed_at=now
            )
            logger.info("gate.rejected_abandoned", gate_id=gate_id, run_id=gate.run_id)
        else:
            # REGENERATE or BRANCH -> transition to REWORKING
            await self.execution_repo.update_run_status(gate.run_id, RunStatus.REWORKING)
            logger.info(
                "gate.rejected_reworking",
                gate_id=gate_id,
                run_id=gate.run_id,
                action=feedback.action,
            )
            # Re-enqueue to trigger rework cycle
            await self.queue_broker.enqueue(gate.run_id)

        return updated_gate, recorded_approval
