"""Repository for Pipeline Execution, Runs, Steps, Gates, Approvals, Locks, and Quota."""

from datetime import datetime

from atlas.adapters.persistence.tables import (
    ApprovalTable,
    GateTable,
    IdempotencyKeyTable,
    ModelCallTable,
    QuotaLedgerTable,
    ResourceLockTable,
    RunTable,
    StepTable,
)
from atlas.domain.execution.models import (
    Approval,
    ApprovalDecision,
    Gate,
    GateStatus,
    GateType,
    IdempotencyKey,
    ModelCall,
    QuotaLedgerEntry,
    ResourceLock,
    Run,
    RunStatus,
    Step,
    StepStatus,
)
from atlas.domain.focus.models import Facet, FocusSnapshot, ScopeMode
from atlas.platform.clock import utc_now
from atlas.platform.errors import (
    GateAlreadyResolvedError,
    GateNotFoundError,
    ResourceLockHeldError,
    RunNotFoundError,
    StepNotFoundError,
)
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession


class ExecutionRepository:
    """Data access repository for workflow execution, state persistence, and durability."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # =========================================================================
    # Runs (Capturing Focus by Value)
    # =========================================================================

    async def create_run(self, run: Run) -> Run:
        """Create a new pipeline Run capturing its Focus by value."""
        row = RunTable(
            id=run.id,
            topic_id=run.topic_id,
            channel_id=run.channel_id,
            status=run.status.value,
            captured_focus=run.captured_focus.model_dump(mode="json"),
            trace_id=run.trace_id,
            actor_id=run.actor_id,
            created_at=run.created_at,
            updated_at=run.updated_at,
            completed_at=run.completed_at,
        )
        self.session.add(row)
        await self.session.flush()
        return run

    async def get_run(self, run_id: str) -> Run:
        """Fetch Run by ID."""
        row = await self.session.get(RunTable, run_id)
        if not row:
            raise RunNotFoundError(run_id)

        focus_data = dict(row.captured_focus)
        facets = [Facet(**f) for f in focus_data.get("facets", [])]
        focus_snapshot = FocusSnapshot(
            focus_id=focus_data["focus_id"],
            scope_mode=ScopeMode(focus_data["scope_mode"]),
            facets=facets,
            entity_id=focus_data.get("entity_id"),
            captured_at=datetime.fromisoformat(focus_data["captured_at"])
            if isinstance(focus_data["captured_at"], str)
            else focus_data["captured_at"],
        )

        return Run(
            id=row.id,
            topic_id=row.topic_id,
            channel_id=row.channel_id,
            status=RunStatus(row.status),
            captured_focus=focus_snapshot,
            trace_id=row.trace_id,
            actor_id=row.actor_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
            completed_at=row.completed_at,
        )

    async def update_run_status(
        self, run_id: str, status: RunStatus, completed_at: datetime | None = None
    ) -> None:
        """Transition a Run state."""
        row = await self.session.get(RunTable, run_id)
        if not row:
            raise RunNotFoundError(run_id)
        row.status = status.value
        row.updated_at = utc_now()
        if completed_at:
            row.completed_at = completed_at
        await self.session.flush()

    # =========================================================================
    # Steps & Checkpointing
    # =========================================================================

    async def create_step(self, step: Step) -> Step:
        """Persist a Step record."""
        row = StepTable(
            id=step.id,
            run_id=step.run_id,
            step_name=step.step_name,
            step_index=step.step_index,
            status=step.status.value,
            input_hash=step.input_hash,
            output_artifact_ref=step.output_artifact_ref,
            error=step.error,
            started_at=step.started_at,
            completed_at=step.completed_at,
        )
        self.session.add(row)
        await self.session.flush()
        return step

    async def get_step(self, step_id: str) -> Step:
        """Fetch Step by ID."""
        row = await self.session.get(StepTable, step_id)
        if not row:
            raise StepNotFoundError(step_id)
        return Step(
            id=row.id,
            run_id=row.run_id,
            step_name=row.step_name,
            step_index=row.step_index,
            status=StepStatus(row.status),
            input_hash=row.input_hash,
            output_artifact_ref=row.output_artifact_ref,
            error=row.error,
            started_at=row.started_at,
            completed_at=row.completed_at,
        )

    async def update_step(
        self,
        step_id: str,
        status: StepStatus,
        output_artifact_ref: str | None = None,
        error: str | None = None,
        completed_at: datetime | None = None,
    ) -> None:
        """Update Step status and checkpoint output artifact reference."""
        row = await self.session.get(StepTable, step_id)
        if not row:
            raise StepNotFoundError(step_id)
        row.status = status.value
        if output_artifact_ref is not None:
            row.output_artifact_ref = output_artifact_ref
        if error is not None:
            row.error = error
        if completed_at is not None:
            row.completed_at = completed_at
        await self.session.flush()

    # =========================================================================
    # Gates & Approvals (Human Suspension)
    # =========================================================================

    async def create_gate(self, gate: Gate) -> Gate:
        """Create a suspension Gate."""
        row = GateTable(
            id=gate.id,
            run_id=gate.run_id,
            step_id=gate.step_id,
            gate_type=gate.gate_type.value,
            status=gate.status.value,
            requested_at=gate.requested_at,
            resolved_at=gate.resolved_at,
        )
        self.session.add(row)
        await self.session.flush()
        return gate

    async def get_gate(self, gate_id: str) -> Gate:
        """Fetch Gate by ID."""
        row = await self.session.get(GateTable, gate_id)
        if not row:
            raise GateNotFoundError(gate_id)
        return Gate(
            id=row.id,
            run_id=row.run_id,
            step_id=row.step_id,
            gate_type=GateType(row.gate_type),
            status=GateStatus(row.status),
            requested_at=row.requested_at,
            resolved_at=row.resolved_at,
        )

    async def record_approval(self, approval: Approval) -> Approval:
        """Record human approval or structured rejection, resolving the Gate."""
        gate_row = await self.session.get(GateTable, approval.gate_id)
        if not gate_row:
            raise GateNotFoundError(approval.gate_id)
        if gate_row.status != GateStatus.PENDING.value:
            raise GateAlreadyResolvedError(gate_row.id, gate_row.status)

        # Update Gate status
        gate_row.status = (
            GateStatus.APPROVED.value
            if approval.decision == ApprovalDecision.APPROVED
            else GateStatus.REJECTED.value
        )
        gate_row.resolved_at = approval.created_at

        # Save Approval row
        approval_row = ApprovalTable(
            id=approval.id,
            gate_id=approval.gate_id,
            run_id=approval.run_id,
            actor_id=approval.actor_id,
            decision=approval.decision.value,
            feedback=approval.feedback.model_dump(mode="json") if approval.feedback else None,
            created_at=approval.created_at,
        )
        self.session.add(approval_row)
        await self.session.flush()
        return approval

    # =========================================================================
    # Resource Locks (GPU Semaphore Lease)
    # =========================================================================

    async def acquire_lock(
        self, resource_name: str, holder_id: str, ttl_seconds: int, priority: int = 0
    ) -> ResourceLock:
        """Acquire a named resource lease if available or expired."""
        now = utc_now()
        existing = await self.session.get(ResourceLockTable, resource_name)

        if existing and existing.expires_at > now and existing.holder_id != holder_id:
            raise ResourceLockHeldError(resource_name, existing.holder_id)

        from datetime import timedelta

        expires_at = now + timedelta(seconds=ttl_seconds)

        if existing:
            existing.holder_id = holder_id
            existing.priority = priority
            existing.acquired_at = now
            existing.expires_at = expires_at
        else:
            new_lock = ResourceLockTable(
                resource_name=resource_name,
                holder_id=holder_id,
                priority=priority,
                acquired_at=now,
                expires_at=expires_at,
            )
            self.session.add(new_lock)

        await self.session.flush()
        return ResourceLock(
            resource_name=resource_name,
            holder_id=holder_id,
            priority=priority,
            acquired_at=now,
            expires_at=expires_at,
        )

    async def release_lock(self, resource_name: str, holder_id: str) -> None:
        """Release a held resource lock."""
        stmt = delete(ResourceLockTable).where(
            (ResourceLockTable.resource_name == resource_name)
            & (ResourceLockTable.holder_id == holder_id)
        )
        await self.session.execute(stmt)
        await self.session.flush()

    # =========================================================================
    # Idempotency Keys
    # =========================================================================

    async def record_idempotency_key(self, item: IdempotencyKey) -> None:
        """Store step output hash against composite idempotency key."""
        row = IdempotencyKeyTable(
            key=item.key,
            step_id=item.step_id,
            output_hash=item.output_hash,
            created_at=item.created_at,
            expires_at=item.expires_at,
        )
        self.session.add(row)
        await self.session.flush()

    async def get_idempotency_key(self, key: str) -> IdempotencyKey | None:
        """Look up idempotency key."""
        row = await self.session.get(IdempotencyKeyTable, key)
        if not row:
            return None
        return IdempotencyKey(
            key=row.key,
            step_id=row.step_id,
            output_hash=row.output_hash,
            created_at=row.created_at,
            expires_at=row.expires_at,
        )

    # =========================================================================
    # Model Calls Audit & Quota Ledger
    # =========================================================================

    async def record_model_call(self, call: ModelCall) -> ModelCall:
        """Record metered model call in audit log."""
        row = ModelCallTable(
            id=call.id,
            run_id=call.run_id,
            step_id=call.step_id,
            provider=call.provider,
            model_id=call.model_id,
            prompt_version=call.prompt_version,
            input_tokens=call.input_tokens,
            output_tokens=call.output_tokens,
            latency_ms=call.latency_ms,
            cached=call.cached,
            outcome=call.outcome,
            cost_usd=call.cost_usd,
            created_at=call.created_at,
        )
        self.session.add(row)
        await self.session.flush()
        return call

    async def record_quota_consumption(self, entry: QuotaLedgerEntry) -> QuotaLedgerEntry:
        """Record consumption in append-only quota ledger."""
        row = QuotaLedgerTable(
            id=entry.id,
            provider=entry.provider,
            window_type=entry.window_type,
            window_start=entry.window_start,
            tokens_consumed=entry.tokens_consumed,
            requests_consumed=entry.requests_consumed,
            run_id=entry.run_id,
            created_at=entry.created_at,
        )
        self.session.add(row)
        await self.session.flush()
        return entry
