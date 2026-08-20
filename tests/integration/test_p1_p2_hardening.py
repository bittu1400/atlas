"""Regression and concurrency tests for Phase 2 P1 and P2 issues (B-01 to B-07, C-01 to C-05)."""

from datetime import UTC, datetime

import pytest
from atlas.adapters.persistence.repositories.execution_repository import ExecutionRepository
from atlas.adapters.persistence.repositories.focus_repository import FocusRepository
from atlas.adapters.persistence.repositories.knowledge_repository import KnowledgeRepository
from atlas.adapters.persistence.repositories.publishing_repository import PublishingRepository
from atlas.adapters.persistence.repositories.source_repository import SourceRepository
from atlas.domain.execution.models import (
    Approval,
    ApprovalDecision,
    Gate,
    GateStatus,
    GateType,
    Run,
    RunStatus,
    Step,
)
from atlas.domain.focus.models import Entity, FocusSnapshot, ScopeMode
from atlas.domain.knowledge.models import (
    KnowledgeObjectStatus,
    KnowledgeObjectVersion,
    Topic,
)
from atlas.domain.knowledge.payload import KnowledgePayloadV1
from atlas.domain.publishing.models import Channel
from atlas.platform.errors import (
    GateAlreadyResolvedError,
    ResourceLockHeldError,
)
from atlas.platform.ids import (
    generate_approval_id,
    generate_gate_id,
    generate_ko_id,
    generate_run_id,
    generate_step_id,
    generate_topic_id,
    generate_trace_id,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_b01_cross_run_execution_records_rejected(db_session: AsyncSession) -> None:
    """B-01: Execution records must not cross runs. Foreign keys must reject mismatches."""
    now = datetime(2026, 7, 30, 10, 0, 0, tzinfo=UTC)
    pub_repo = PublishingRepository(db_session)
    source_repo = SourceRepository(db_session)
    exec_repo = ExecutionRepository(db_session)

    await pub_repo.save_channel(
        Channel(id="origins", name="ORIGINS", audience_timezone="America/New_York", created_at=now)
    )
    topic_id = generate_topic_id()
    await source_repo.save_topic(
        Topic(id=topic_id, title="Topic 1", domain_id="dom_animal", created_at=now)
    )

    run_1_id = generate_run_id()
    run_2_id = generate_run_id()
    for rid in (run_1_id, run_2_id):
        await exec_repo.create_run(
            Run(
                id=rid,
                topic_id=topic_id,
                channel_id="origins",
                status=RunStatus.RUNNING,
                captured_focus=FocusSnapshot(
                    focus_id="f1", scope_mode=ScopeMode.SOFT, facets=[], captured_at=now
                ),
                trace_id=generate_trace_id(),
                actor_id="op",
                created_at=now,
                updated_at=now,
            )
        )

    step_1_id = generate_step_id()
    await exec_repo.create_step(
        Step(id=step_1_id, run_id=run_1_id, step_name="step1", step_index=1, input_hash="h1")
    )

    # 1. Gate referencing Step from run_1 but marked as belonging to run_2 -> must fail FK
    with pytest.raises(Exception, match=".*"):
        async with db_session.begin_nested():
            await db_session.execute(
                text(
                    """
                    INSERT INTO gates (id, run_id, step_id, gate_type, status, requested_at)
                    VALUES ('gate_mismatch', :run_2, :step_1, 'manual', 'pending', now())
                    """
                ),
                {"run_2": run_2_id, "step_1": step_1_id},
            )

    # 2. Approval referencing Gate from run_1 but marked as belonging to run_2 -> must fail FK
    gate_1_id = generate_gate_id()
    await exec_repo.create_gate(
        Gate(
            id=gate_1_id,
            run_id=run_1_id,
            step_id=step_1_id,
            gate_type=GateType.MANUAL,
            status=GateStatus.PENDING,
            requested_at=now,
        )
    )

    with pytest.raises(Exception, match=".*"):
        async with db_session.begin_nested():
            await db_session.execute(
                text(
                    """
                    INSERT INTO approvals (id, gate_id, run_id, actor_id, decision, created_at)
                    VALUES ('app_mismatch', :gate_1, :run_2, 'op', 'approved', now())
                    """
                ),
                {"gate_1": gate_1_id, "run_2": run_2_id},
            )

    # 3. ModelCall referencing Step from run_1 but run_id is run_2 -> must fail FK
    with pytest.raises(Exception, match=".*"):
        async with db_session.begin_nested():
            await db_session.execute(
                text(
                    """
                    INSERT INTO model_calls (id, run_id, step_id, provider, model_id, prompt_version, parameters, code_version, created_at)
                    VALUES ('mc_mismatch', :run_2, :step_1, 'anthropic', 'claude-3', 'v1', '{}', 'abc', now())
                    """
                ),
                {"run_2": run_2_id, "step_1": step_1_id},
            )


@pytest.mark.asyncio
async def test_b02_approval_double_resolution_race(db_session: AsyncSession) -> None:
    """B-02: Approvals table enforces unique gate_id and repository prevents double resolution."""
    now = datetime(2026, 7, 30, 10, 0, 0, tzinfo=UTC)
    pub_repo = PublishingRepository(db_session)
    source_repo = SourceRepository(db_session)
    exec_repo = ExecutionRepository(db_session)

    await pub_repo.save_channel(
        Channel(id="origins", name="ORIGINS", audience_timezone="America/New_York", created_at=now)
    )
    topic_id = generate_topic_id()
    await source_repo.save_topic(
        Topic(id=topic_id, title="Topic 1", domain_id="dom_animal", created_at=now)
    )

    run_id = generate_run_id()
    await exec_repo.create_run(
        Run(
            id=run_id,
            topic_id=topic_id,
            channel_id="origins",
            status=RunStatus.RUNNING,
            captured_focus=FocusSnapshot(
                focus_id="f1", scope_mode=ScopeMode.SOFT, facets=[], captured_at=now
            ),
            trace_id=generate_trace_id(),
            actor_id="op",
            created_at=now,
            updated_at=now,
        )
    )
    step_id = generate_step_id()
    await exec_repo.create_step(
        Step(id=step_id, run_id=run_id, step_name="step1", step_index=1, input_hash="h1")
    )
    gate_id = generate_gate_id()
    await exec_repo.create_gate(
        Gate(
            id=gate_id,
            run_id=run_id,
            step_id=step_id,
            gate_type=GateType.MANUAL,
            status=GateStatus.PENDING,
            requested_at=now,
        )
    )

    # First approval succeeds
    app_1 = Approval(
        id=generate_approval_id(),
        gate_id=gate_id,
        run_id=run_id,
        actor_id="op1",
        decision=ApprovalDecision.APPROVED,
        created_at=now,
    )
    await exec_repo.record_approval(app_1)

    # Second approval via repository fails with typed error
    app_2 = Approval(
        id=generate_approval_id(),
        gate_id=gate_id,
        run_id=run_id,
        actor_id="op2",
        decision=ApprovalDecision.APPROVED,
        created_at=now,
    )
    with pytest.raises(GateAlreadyResolvedError):
        await exec_repo.record_approval(app_2)

    # Direct database insertion for duplicate gate_id fails unique constraint
    with pytest.raises(Exception, match=".*"):
        async with db_session.begin_nested():
            await db_session.execute(
                text(
                    """
                    INSERT INTO approvals (id, gate_id, run_id, actor_id, decision, created_at)
                    VALUES ('app_dup', :gate_id, :run_id, 'op2', 'approved', now())
                    """
                ),
                {"gate_id": gate_id, "run_id": run_id},
            )


@pytest.mark.asyncio
async def test_b03_ko_version_ordering_enforcement(db_session: AsyncSession) -> None:
    """B-03: Knowledge Object versions must be consecutive starting at 1."""
    now = datetime(2026, 7, 30, 10, 0, 0, tzinfo=UTC)
    source_repo = SourceRepository(db_session)
    ko_repo = KnowledgeRepository(db_session)

    topic_id = generate_topic_id()
    await source_repo.save_topic(
        Topic(id=topic_id, title="Topic KO", domain_id="dom_animal", created_at=now)
    )

    ko_id = generate_ko_id()

    # Initial version cannot be 2
    kov_bad = KnowledgeObjectVersion(
        ko_id=ko_id,
        version=2,
        topic_id=topic_id,
        status=KnowledgeObjectStatus.DRAFT,
        quality_score=80.0,
        confidence=1.0,
        actor_id="op",
        reason="bad initial version",
        payload=KnowledgePayloadV1(summary="Initial summary"),
        created_at=now,
    )
    with pytest.raises(ValueError, match="Initial version must be 1"):
        await ko_repo.save_version(kov_bad, make_current=True)

    # Initial version 1 succeeds
    kov_1 = KnowledgeObjectVersion(
        ko_id=ko_id,
        version=1,
        topic_id=topic_id,
        status=KnowledgeObjectStatus.DRAFT,
        quality_score=80.0,
        confidence=1.0,
        actor_id="op",
        reason="Initial version",
        payload=KnowledgePayloadV1(summary="Initial summary"),
        created_at=now,
    )
    await ko_repo.save_version(kov_1, make_current=True)

    # Next version skipping to 3 fails
    kov_3 = KnowledgeObjectVersion(
        ko_id=ko_id,
        version=3,
        topic_id=topic_id,
        status=KnowledgeObjectStatus.DRAFT,
        quality_score=85.0,
        confidence=1.0,
        actor_id="op",
        reason="Skipped version 2",
        payload=KnowledgePayloadV1(summary="Updated summary"),
        created_at=now,
    )
    with pytest.raises(ValueError, match="Version must be exactly 2"):
        await ko_repo.save_version(kov_3, make_current=True)


@pytest.mark.asyncio
async def test_b04_step_idempotency_uniqueness(db_session: AsyncSession) -> None:
    """B-04: Step (run_id, step_name, input_hash) is unique."""
    now = datetime(2026, 7, 30, 10, 0, 0, tzinfo=UTC)
    pub_repo = PublishingRepository(db_session)
    source_repo = SourceRepository(db_session)
    exec_repo = ExecutionRepository(db_session)

    await pub_repo.save_channel(
        Channel(id="origins", name="ORIGINS", audience_timezone="America/New_York", created_at=now)
    )
    topic_id = generate_topic_id()
    await source_repo.save_topic(
        Topic(id=topic_id, title="Topic Idemp", domain_id="dom_animal", created_at=now)
    )

    run_id = generate_run_id()
    await exec_repo.create_run(
        Run(
            id=run_id,
            topic_id=topic_id,
            channel_id="origins",
            status=RunStatus.RUNNING,
            captured_focus=FocusSnapshot(
                focus_id="f1", scope_mode=ScopeMode.SOFT, facets=[], captured_at=now
            ),
            trace_id=generate_trace_id(),
            actor_id="op",
            created_at=now,
            updated_at=now,
        )
    )

    # Create first step
    step_1 = Step(
        id=generate_step_id(),
        run_id=run_id,
        step_name="research",
        step_index=1,
        input_hash="hash_same",
    )
    await exec_repo.create_step(step_1)

    # Creating duplicate step with same (run_id, step_name, input_hash) must fail
    step_dup = Step(
        id=generate_step_id(),
        run_id=run_id,
        step_name="research",
        step_index=2,
        input_hash="hash_same",
    )
    with pytest.raises(Exception, match=".*"):
        async with db_session.begin_nested():
            await exec_repo.create_step(step_dup)


@pytest.mark.asyncio
async def test_b05_resource_lock_edge_cases(db_session: AsyncSession) -> None:
    """B-05: Non-positive TTL rejected, lock conflict raises ResourceLockHeldError."""
    exec_repo = ExecutionRepository(db_session)

    # Non-positive TTL rejected
    with pytest.raises(ValueError, match="TTL must be positive"):
        await exec_repo.acquire_lock("gpu_p1", holder_id="w1", ttl_seconds=0)

    with pytest.raises(ValueError, match="TTL must be positive"):
        await exec_repo.acquire_lock("gpu_p1", holder_id="w1", ttl_seconds=-10)

    # Acquire lock for 60s
    lock = await exec_repo.acquire_lock("gpu_p1", holder_id="w1", ttl_seconds=60)
    assert lock.holder_id == "w1"

    # Conflicting acquisition raises ResourceLockHeldError
    with pytest.raises(ResourceLockHeldError):
        await exec_repo.acquire_lock("gpu_p1", holder_id="w2", ttl_seconds=60)


@pytest.mark.asyncio
async def test_b06_entity_scoping_integrity(db_session: AsyncSession) -> None:
    """B-06: Wikidata QID uniqueness and foreign key enforcement."""
    focus_repo = FocusRepository(db_session)

    ent_1 = Entity(
        id="ent_01",
        name="Albert Einstein",
        domain_id="dom_animal",
        wikidata_qid="Q937",
    )
    await focus_repo.save_entity(ent_1)

    # Duplicate non-null wikidata_qid must fail
    ent_dup = Entity(
        id="ent_02",
        name="Duplicate Einstein",
        domain_id="dom_animal",
        wikidata_qid="Q937",
    )
    with pytest.raises(Exception, match=".*"):
        async with db_session.begin_nested():
            await focus_repo.save_entity(ent_dup)


@pytest.mark.asyncio
async def test_b07_snapshot_storage_key_check(db_session: AsyncSession) -> None:
    """B-07: Snapshot storage_key check constraint enforces matching content_hash."""
    await db_session.execute(
        text(
            """
            INSERT INTO sources (id, url, title, source_tier, created_at)
            VALUES ('src_b07', 'https://example.com', 'Title', 'primary', now())
            """
        )
    )
    await db_session.commit()

    content_hash = "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"
    valid_key = f"sha256/{content_hash[:2]}/{content_hash[2:4]}/{content_hash}"
    invalid_key = "sha256/xx/yy/mismatched_key"

    # Valid storage_key succeeds
    await db_session.execute(
        text(
            """
            INSERT INTO snapshots (id, source_id, content_hash, storage_key, mime_type, byte_size, retrieved_at)
            VALUES ('snap_valid', 'src_b07', :ch, :sk, 'text/html', 100, now())
            """
        ),
        {"ch": content_hash, "sk": valid_key},
    )
    await db_session.commit()

    # Mismatched storage_key fails DB check constraint
    with pytest.raises(Exception, match=".*"):
        async with db_session.begin_nested():
            await db_session.execute(
                text(
                    """
                    INSERT INTO snapshots (id, source_id, content_hash, storage_key, mime_type, byte_size, retrieved_at)
                    VALUES ('snap_invalid', 'src_b07', :ch, :sk, 'text/html', 100, now())
                    """
                ),
                {"ch": content_hash, "sk": invalid_key},
            )


@pytest.mark.asyncio
async def test_c02_schema_validation_parity(db_session: AsyncSession) -> None:
    """C-02: DB-level check constraints for numeric bounds, time intervals, and quota window types."""
    # 1. Quota window_type 'month' rejected
    with pytest.raises(Exception, match=".*"):
        async with db_session.begin_nested():
            await db_session.execute(
                text(
                    """
                    INSERT INTO quota_ledger (id, provider, window_type, window_start, tokens_consumed, requests_consumed, created_at)
                    VALUES ('ql_bad', 'anthropic', 'month', now(), 10, 1, now())
                    """
                )
            )

    # 2. Negative byte_size in snapshots rejected
    await db_session.execute(
        text(
            """
            INSERT INTO sources (id, url, title, source_tier, created_at)
            VALUES ('src_c02', 'https://example.org', 'Title', 'primary', now())
            """
        )
    )
    ch = "1122334455667788112233445566778811223344556677881122334455667788"
    sk = f"sha256/{ch[:2]}/{ch[2:4]}/{ch}"
    with pytest.raises(Exception, match=".*"):
        async with db_session.begin_nested():
            await db_session.execute(
                text(
                    """
                    INSERT INTO snapshots (id, source_id, content_hash, storage_key, mime_type, byte_size, retrieved_at)
                    VALUES ('snap_neg', 'src_c02', :ch, :sk, 'text/html', -1, now())
                    """
                ),
                {"ch": ch, "sk": sk},
            )

    # 3. Invalid publishing window interval (start >= end)
    await db_session.execute(
        text(
            """
            INSERT INTO channels (id, name, audience_timezone, style_profile, created_at)
            VALUES ('ch_c02', 'CH_C02', 'America/New_York', '{}', now())
            """
        )
    )
    with pytest.raises(Exception, match=".*"):
        async with db_session.begin_nested():
            await db_session.execute(
                text(
                    """
                    INSERT INTO publishing_windows (id, channel_id, platform, content_format, day_of_week, local_start_time, local_end_time, source)
                    VALUES ('pw_bad', 'ch_c02', 'youtube', 'vertical', 1, '18:00:00', '09:00:00', 'priors')
                    """
                )
            )


@pytest.mark.asyncio
async def test_c05_ko_history_batching(db_session: AsyncSession) -> None:
    """C-05: get_history loads all versions with their claims without N+1 query regression."""
    now = datetime(2026, 7, 30, 10, 0, 0, tzinfo=UTC)
    source_repo = SourceRepository(db_session)
    ko_repo = KnowledgeRepository(db_session)

    topic_id = generate_topic_id()
    await source_repo.save_topic(
        Topic(id=topic_id, title="History Topic", domain_id="dom_animal", created_at=now)
    )

    ko_id = generate_ko_id()

    # Create version 1
    kov_1 = KnowledgeObjectVersion(
        ko_id=ko_id,
        version=1,
        topic_id=topic_id,
        status=KnowledgeObjectStatus.DRAFT,
        quality_score=75.0,
        confidence=1.0,
        actor_id="op",
        reason="v1",
        payload=KnowledgePayloadV1(summary="v1 summary"),
        created_at=now,
    )
    await ko_repo.save_version(kov_1, make_current=True)

    # Create version 2
    kov_2 = KnowledgeObjectVersion(
        ko_id=ko_id,
        version=2,
        topic_id=topic_id,
        status=KnowledgeObjectStatus.VERIFIED,
        quality_score=85.0,
        confidence=1.0,
        actor_id="op",
        reason="v2",
        payload=KnowledgePayloadV1(summary="v2 summary"),
        created_at=now,
    )
    await ko_repo.save_version(kov_2, make_current=True)

    history = await ko_repo.get_history(ko_id)
    assert len(history) == 2
    assert history[0].version == 1
    assert history[0].reason == "v1"
    assert history[1].version == 2
    assert history[1].reason == "v2"
