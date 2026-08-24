from atlas.application.ports.queue import QueueBroker
from atlas.application.ports.repositories import ExecutionRepositoryPort
from atlas.domain.execution.models import (
    Approval,
    ApprovalDecision,
    Gate,
    GateStatus,
    RunStatus,
)
from atlas.platform.clock import utc_now
from atlas.platform.errors import GateAlreadyResolvedError, GateNotFoundError
from atlas.platform.ids import generate_approval_id
from atlas.platform.logging import get_logger

logger = get_logger("usecases.approve_gate")


class ApproveGateUseCase:
    """Use case to grant operator approval at a Gate and resume execution."""

    def __init__(
        self,
        execution_repo: ExecutionRepositoryPort,
        queue_broker: QueueBroker,
    ) -> None:
        self.execution_repo = execution_repo
        self.queue_broker = queue_broker

    async def execute(self, gate_id: str, actor_id: str = "operator") -> tuple[Gate, Approval]:
        """Approve a pending Gate and resume the pipeline."""
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
            decision=ApprovalDecision.APPROVED,
            created_at=now,
        )

        # Record approval and resolve gate in DB transaction
        recorded_approval = await self.execution_repo.record_approval(approval)
        updated_gate = Gate(
            id=gate.id,
            run_id=gate.run_id,
            step_id=gate.step_id,
            gate_type=gate.gate_type,
            status=GateStatus.APPROVED,
            requested_at=gate.requested_at,
            resolved_at=now,
        )

        # Transition Run status back to RUNNING
        await self.execution_repo.update_run_status(gate.run_id, RunStatus.RUNNING)
        logger.info("gate.approved_resuming", gate_id=gate_id, run_id=gate.run_id, actor=actor_id)

        # Re-enqueue pipeline to resume from next step
        await self.queue_broker.enqueue(gate.run_id)

        return updated_gate, recorded_approval
