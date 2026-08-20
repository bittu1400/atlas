"""Integration tests for Pipeline Execution, State Machine, Locks, and Quota (ADR-0001)."""

from datetime import UTC, datetime

import pytest
from atlas.adapters.persistence.repositories.execution_repository import ExecutionRepository
from atlas.adapters.persistence.repositories.focus_repository import FocusRepository
from atlas.adapters.persistence.repositories.publishing_repository import PublishingRepository
from atlas.adapters.persistence.repositories.source_repository import SourceRepository
from atlas.domain.execution.models import (
    Approval,
    ApprovalDecision,
    Gate,
    GateStatus,
    GateType,
    IdempotencyKey,
    RejectionAction,
    RejectionFeedback,
    Run,
    RunStatus,
    Step,
    StepStatus,
)
from atlas.domain.focus.models import (
    Facet,
    Focus,
    FocusSnapshot,
    ScopeMode,
)
from atlas.domain.knowledge.models import Topic
from atlas.domain.publishing.models import Channel
from atlas.platform.errors import (
    GateAlreadyResolvedError,
    ResourceLockHeldError,
)
from atlas.platform.ids import (
    generate_approval_id,
    generate_focus_id,
    generate_gate_id,
    generate_run_id,
    generate_step_id,
    generate_topic_id,
    generate_trace_id,
)
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_run_captures_focus_by_value(db_session: AsyncSession) -> None:
    """Invariant: A Run captures its Focus by value at creation (ADR-0002)."""
    source_repo = SourceRepository(db_session)
    focus_repo = FocusRepository(db_session)
    exec_repo = ExecutionRepository(db_session)
    now = datetime(2026, 7, 30, 10, 0, 0, tzinfo=UTC)

    # 1. Create Channel, Topic & Initial Focus
    pub_repo = PublishingRepository(db_session)
    await pub_repo.save_channel(
        Channel(
            id="origins",
            name="ORIGINS",
            audience_timezone="America/New_York",
            created_at=now,
        )
    )

    topic_id = generate_topic_id()
    await source_repo.save_topic(
        Topic(
            id=topic_id, title="Quantum Computing Origins", domain_id="dom_animal", created_at=now
        )
    )

    focus1_id = generate_focus_id()
    focus1 = Focus(
        id=focus1_id,
        name="Focus 1",
        scope_mode=ScopeMode.SOFT,
        facets=[Facet(dimension="domain", value="Technology")],
        actor_id="operator_01",
        created_at=now,
    )
    await focus_repo.save_focus(focus1)
    await focus_repo.set_active_focus(focus1_id, actor_id="operator_01")

    # 2. Create Run capturing focus1 by value
    run_id = generate_run_id()
    run = Run(
        id=run_id,
        topic_id=topic_id,
        channel_id="origins",
        status=RunStatus.PENDING,
        captured_focus=FocusSnapshot(
            focus_id=focus1.id,
            scope_mode=focus1.scope_mode,
            facets=focus1.facets,
            entity_id=focus1.entity_id,
            captured_at=now,
        ),
        trace_id=generate_trace_id(),
        actor_id="operator_01",
        created_at=now,
        updated_at=now,
    )
    await exec_repo.create_run(run)

    # 3. Change Active Focus to a new Focus 2
    focus2_id = generate_focus_id()
    focus2 = Focus(
        id=focus2_id,
        name="Focus 2",
        scope_mode=ScopeMode.HARD,
        facets=[Facet(dimension="domain", value="History")],
        actor_id="operator_02",
        created_at=now,
    )
    await focus_repo.save_focus(focus2)
    await focus_repo.set_active_focus(focus2_id, actor_id="operator_02")

    # 4. Fetch Run and verify its captured focus is STILL Focus 1
    retrieved_run = await exec_repo.get_run(run_id)
    assert retrieved_run.captured_focus.focus_id == focus1_id
    assert retrieved_run.captured_focus.scope_mode == ScopeMode.SOFT
    assert retrieved_run.captured_focus.facets[0].value == "Technology"


@pytest.mark.asyncio
async def test_step_idempotency_and_checkpointing(db_session: AsyncSession) -> None:
    """Verify Step idempotency key tracking and checkpointing."""
    source_repo = SourceRepository(db_session)
    exec_repo = ExecutionRepository(db_session)
    now = datetime(2026, 7, 30, 10, 0, 0, tzinfo=UTC)

    pub_repo = PublishingRepository(db_session)
    await pub_repo.save_channel(
        Channel(id="origins", name="ORIGINS", audience_timezone="America/New_York", created_at=now)
    )

    topic_id = generate_topic_id()
    await source_repo.save_topic(
        Topic(id=topic_id, title="Test Topic", domain_id="dom_animal", created_at=now)
    )

    run_id = generate_run_id()
    run = Run(
        id=run_id,
        topic_id=topic_id,
        channel_id="origins",
        status=RunStatus.RUNNING,
        captured_focus=FocusSnapshot(
            focus_id="foc_test",
            scope_mode=ScopeMode.SOFT,
            facets=[],
            captured_at=now,
        ),
        trace_id=generate_trace_id(),
        actor_id="operator",
        created_at=now,
        updated_at=now,
    )
    await exec_repo.create_run(run)

    step_id = generate_step_id()
    step = Step(
        id=step_id,
        run_id=run_id,
        step_name="research",
        step_index=3,
        status=StepStatus.RUNNING,
        input_hash="hash_input_12345",
        started_at=now,
    )
    await exec_repo.create_step(step)

    # Record idempotency key
    idempotency_key = f"{run_id}:research:hash_input_12345"
    await exec_repo.record_idempotency_key(
        IdempotencyKey(
            key=idempotency_key,
            step_id=step_id,
            output_hash="hash_output_67890",
            created_at=now,
        )
    )

    # Check idempotency lookup
    key_record = await exec_repo.get_idempotency_key(idempotency_key)
    assert key_record is not None
    assert key_record.step_id == step_id
    assert key_record.output_hash == "hash_output_67890"

    # Checkpoint step output
    await exec_repo.update_step(
        step_id=step_id,
        status=StepStatus.SUCCEEDED,
        output_artifact_ref="var/artifacts/ko_v1.json",
        completed_at=now,
    )

    updated_step = await exec_repo.get_step(step_id)
    assert updated_step.status == StepStatus.SUCCEEDED
    assert updated_step.output_artifact_ref == "var/artifacts/ko_v1.json"


@pytest.mark.asyncio
async def test_gate_suspension_and_structured_rejection(db_session: AsyncSession) -> None:
    """Verify Gate creation, human rejection with structured feedback, and double-resolution prevention."""
    source_repo = SourceRepository(db_session)
    exec_repo = ExecutionRepository(db_session)
    pub_repo = PublishingRepository(db_session)
    now = datetime(2026, 7, 30, 10, 0, 0, tzinfo=UTC)

    await pub_repo.save_channel(
        Channel(id="origins", name="ORIGINS", audience_timezone="America/New_York", created_at=now)
    )

    topic_id = generate_topic_id()
    await source_repo.save_topic(
        Topic(id=topic_id, title="Topic", domain_id="dom_animal", created_at=now)
    )

    run_id = generate_run_id()
    await exec_repo.create_run(
        Run(
            id=run_id,
            topic_id=topic_id,
            channel_id="origins",
            status=RunStatus.SUSPENDED,
            captured_focus=FocusSnapshot(
                focus_id="foc_1", scope_mode=ScopeMode.SOFT, facets=[], captured_at=now
            ),
            trace_id=generate_trace_id(),
            actor_id="operator",
            created_at=now,
            updated_at=now,
        )
    )

    step_id = generate_step_id()
    await exec_repo.create_step(
        Step(id=step_id, run_id=run_id, step_name="script_review", step_index=8, input_hash="h1")
    )

    gate_id = generate_gate_id()
    gate = Gate(
        id=gate_id,
        run_id=run_id,
        step_id=step_id,
        gate_type=GateType.MANUAL,
        status=GateStatus.PENDING,
        requested_at=now,
    )
    await exec_repo.create_gate(gate)

    # Human Rejection with Structured Feedback (SPEC §7)
    feedback = RejectionFeedback(
        target_ref="beat_02",
        rubric_dimension="Hook strength",
        reason="The opening sentence is too abstract; lead with the exact archaeological discovery year.",
        action=RejectionAction.REGENERATE,
    )
    approval = Approval(
        id=generate_approval_id(),
        gate_id=gate_id,
        run_id=run_id,
        actor_id="operator_01",
        decision=ApprovalDecision.REJECTED,
        feedback=feedback,
        created_at=now,
    )
    await exec_repo.record_approval(approval)

    # Gate is now rejected
    resolved_gate = await exec_repo.get_gate(gate_id)
    assert resolved_gate.status == GateStatus.REJECTED
    assert resolved_gate.resolved_at == now

    # Attempting to resolve again must fail
    with pytest.raises(GateAlreadyResolvedError):
        await exec_repo.record_approval(approval)


@pytest.mark.asyncio
async def test_resource_lock_semaphore(db_session: AsyncSession) -> None:
    """Verify GPU semaphore lease acquisition, conflict blocking, and release."""
    repo = ExecutionRepository(db_session)

    # Worker 1 acquires GPU lease for 60s
    lock1 = await repo.acquire_lock("gpu", holder_id="worker_01", ttl_seconds=60, priority=1)
    assert lock1.holder_id == "worker_01"

    # Worker 2 attempts to acquire held lease -> blocked
    with pytest.raises(ResourceLockHeldError):
        await repo.acquire_lock("gpu", holder_id="worker_02", ttl_seconds=60, priority=1)

    # Worker 1 releases lease
    await repo.release_lock("gpu", holder_id="worker_01")

    # Worker 2 can now acquire lease
    lock2 = await repo.acquire_lock("gpu", holder_id="worker_02", ttl_seconds=60, priority=1)
    assert lock2.holder_id == "worker_02"
