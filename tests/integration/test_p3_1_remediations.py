"""Integration tests covering Phase 3.1 remediated execution state machine, runner error handling, and API security."""

import json
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from atlas.adapters.persistence.repositories.execution_repository import ExecutionRepository
from atlas.adapters.persistence.repositories.focus_repository import FocusRepository
from atlas.adapters.persistence.repositories.knowledge_repository import KnowledgeRepository
from atlas.adapters.persistence.repositories.publishing_repository import PublishingRepository
from atlas.adapters.persistence.repositories.source_repository import SourceRepository
from atlas.adapters.storage.local import LocalStorage
from atlas.application.pipeline.runner import PipelineRunner
from atlas.application.policies.gate_policy import PipelineStage
from atlas.application.usecases.get_run_status import GetQuotaStatusUseCase, ListGatesUseCase
from atlas.domain.execution.models import (
    Approval,
    ApprovalDecision,
    Gate,
    GateStatus,
    GateType,
    QuotaLedgerEntry,
    Run,
    RunStatus,
    Step,
    StepStatus,
    WindowType,
)
from atlas.domain.focus.models import Domain, FocusSnapshot, ResearchProfile, ScopeMode
from atlas.domain.knowledge.models import Topic, TopicStatus
from atlas.platform.clock import utc_now
from atlas.platform.config import get_settings
from atlas.platform.errors import (
    GateAlreadyResolvedError,
    InvalidStateTransitionError,
    StepExecutionError,
)
from atlas.platform.quota import QuotaManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import (
    get_db_session,
    get_execution_repository,
    get_focus_repository,
    get_knowledge_repository,
    get_publishing_repository,
    get_source_repository,
    get_storage,
)
from apps.api.main import app
from apps.api.routes.events import event_generator


async def _seed_prerequisites(
    focus_repo: FocusRepository,
    src_repo: SourceRepository,
    topic_id: str,
) -> None:
    """Seed Domain and Topic rows for foreign key constraints."""
    domain = Domain(
        id=f"dom_{uuid.uuid4().hex[:8]}",
        name="Science & History",
        description="Historical and scientific research domain",
        research_profile=ResearchProfile(
            preferred_apis=["openalex", "smithsonian"],
            source_allowlist=["*.org", "*.edu"],
        ),
    )
    await focus_repo.save_domain(domain)

    topic = Topic(
        id=topic_id,
        title=f"History of {topic_id}",
        domain_id=domain.id,
        status=TopicStatus.PROPOSED,
        created_at=utc_now(),
    )
    await src_repo.save_topic(topic)


@pytest.fixture
def test_storage(tmp_path: str) -> LocalStorage:
    return LocalStorage(root_dir=str(tmp_path))


@pytest.fixture
def api_client(db_session: AsyncSession, test_storage: LocalStorage) -> AsyncClient:
    """Create HTTP client with dependency overrides for test session."""

    async def _override_get_db_session() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db_session] = _override_get_db_session
    app.dependency_overrides[get_execution_repository] = lambda: ExecutionRepository(db_session)
    app.dependency_overrides[get_focus_repository] = lambda: FocusRepository(db_session)
    app.dependency_overrides[get_knowledge_repository] = lambda: KnowledgeRepository(db_session)
    app.dependency_overrides[get_source_repository] = lambda: SourceRepository(db_session)
    app.dependency_overrides[get_publishing_repository] = lambda: PublishingRepository(db_session)
    app.dependency_overrides[get_storage] = lambda: test_storage
    from atlas.adapters.fakes.providers import FakeQueueBroker

    from apps.api.dependencies import get_queue_broker

    app.dependency_overrides[get_queue_broker] = lambda: FakeQueueBroker()

    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://testserver")


@pytest.mark.asyncio
async def test_run_state_transition_validation(db_session: AsyncSession) -> None:
    """P2-07: InvalidStateTransitionError is raised on invalid state transitions."""
    repo = ExecutionRepository(db_session)
    focus_repo = FocusRepository(db_session)
    source_repo = SourceRepository(db_session)
    now = utc_now()

    topic_id = f"topic_{uuid.uuid4().hex[:8]}"
    await _seed_prerequisites(focus_repo, source_repo, topic_id)

    focus = FocusSnapshot(
        focus_id=f"focus_{uuid.uuid4().hex[:8]}",
        scope_mode=ScopeMode.EXPLORATORY,
        facets=[],
        captured_at=now,
    )
    run = Run(
        id=f"run_trans_{uuid.uuid4().hex[:8]}",
        topic_id=topic_id,
        channel_id="origins",
        status=RunStatus.PENDING,
        captured_focus=focus,
        trace_id="tr_trans",
        actor_id="operator",
        created_at=now,
        updated_at=now,
    )
    await repo.create_run(run)

    # Valid: PENDING -> RUNNING
    await repo.update_run_status(run.id, RunStatus.RUNNING)
    updated = await repo.get_run(run.id)
    assert updated.status == RunStatus.RUNNING

    # Valid: RUNNING -> SUSPENDED
    await repo.update_run_status(run.id, RunStatus.SUSPENDED)
    updated = await repo.get_run(run.id)
    assert updated.status == RunStatus.SUSPENDED

    # Valid: SUSPENDED -> RUNNING
    await repo.update_run_status(run.id, RunStatus.RUNNING)

    # Valid: RUNNING -> COMPLETED (terminal)
    await repo.update_run_status(run.id, RunStatus.COMPLETED, completed_at=utc_now())
    updated = await repo.get_run(run.id)
    assert updated.status == RunStatus.COMPLETED

    # Invalid: COMPLETED -> RUNNING (terminal state cannot transition)
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        await repo.update_run_status(run.id, RunStatus.RUNNING)
    assert exc_info.value.current_state == RunStatus.COMPLETED.value
    assert exc_info.value.target_state == RunStatus.RUNNING.value


@pytest.mark.asyncio
async def test_gate_already_resolved_error(db_session: AsyncSession) -> None:
    """P2-08: Attempting to resolve an already-resolved gate raises GateAlreadyResolvedError."""
    repo = ExecutionRepository(db_session)
    focus_repo = FocusRepository(db_session)
    source_repo = SourceRepository(db_session)
    now = utc_now()

    topic_id = f"topic_{uuid.uuid4().hex[:8]}"
    await _seed_prerequisites(focus_repo, source_repo, topic_id)

    run_id = f"run_gate_{uuid.uuid4().hex[:8]}"
    focus = FocusSnapshot(
        focus_id="focus_gate",
        scope_mode=ScopeMode.EXPLORATORY,
        facets=[],
        captured_at=now,
    )
    run = Run(
        id=run_id,
        topic_id=topic_id,
        channel_id="origins",
        status=RunStatus.RUNNING,
        captured_focus=focus,
        trace_id="tr_gate",
        actor_id="operator",
        created_at=now,
        updated_at=now,
    )
    await repo.create_run(run)

    step_id = f"step_{run_id}_topic_selection"
    step = Step(
        id=step_id,
        run_id=run_id,
        step_name="topic_selection",
        step_index=2,
        status=StepStatus.SUSPENDED,
        input_hash="hash",
    )
    await repo.create_step(step)

    gate_id = f"gt_{uuid.uuid4().hex[:8]}"
    gate = Gate(
        id=gate_id,
        run_id=run_id,
        step_id=step_id,
        gate_type=GateType.MANUAL,
        status=GateStatus.PENDING,
        requested_at=now,
    )
    await repo.create_gate(gate)

    # First resolution: succeed
    app1 = Approval(
        id=f"app_{uuid.uuid4().hex[:8]}",
        gate_id=gate_id,
        run_id=run_id,
        actor_id="operator",
        decision=ApprovalDecision.APPROVED,
        created_at=now,
    )
    await repo.record_approval(app1)

    # Second resolution: should raise GateAlreadyResolvedError
    app2 = Approval(
        id=f"app_{uuid.uuid4().hex[:8]}",
        gate_id=gate_id,
        run_id=run_id,
        actor_id="operator",
        decision=ApprovalDecision.APPROVED,
        created_at=now,
    )
    with pytest.raises(GateAlreadyResolvedError):
        await repo.record_approval(app2)


@pytest.mark.asyncio
async def test_quota_ledger_summary_and_usecase(db_session: AsyncSession) -> None:
    """P1-03: ExecutionRepository aggregates quota consumption and GetQuotaStatusUseCase reflects it."""
    repo = ExecutionRepository(db_session)
    now = utc_now()

    # Record 150 tokens in day window for gemini
    entry = QuotaLedgerEntry(
        id=f"ql_{uuid.uuid4().hex[:8]}",
        provider="gemini",
        window_type=WindowType.DAY,
        window_start=now,
        tokens_consumed=150,
        requests_consumed=2,
        created_at=now,
    )
    await repo.record_quota_consumption(entry)

    summary = await repo.get_quota_consumption_summary()
    assert "gemini" in summary
    assert summary["gemini"]["daily_tokens"] >= 150
    assert summary["gemini"]["daily_requests"] >= 2

    # Query through use case
    use_case = GetQuotaStatusUseCase(repo)
    res = await use_case.execute()
    assert res["status"] == "healthy"
    assert "gemini" in res["providers"]


@pytest.mark.asyncio
async def test_list_all_gates_usecase(db_session: AsyncSession) -> None:
    """P1-04: ListGatesUseCase returns all gates when pending_only=False."""
    repo = ExecutionRepository(db_session)
    use_case = ListGatesUseCase(repo)

    all_gates = await use_case.execute(pending_only=False)
    assert isinstance(all_gates, list)


@pytest.mark.asyncio
async def test_runner_stage_failure_handling(db_session: AsyncSession) -> None:
    """P0-02 & P3-04: Runner catches exceptions, updates step/run status to FAILED with error, and raises StepExecutionError."""
    settings = get_settings()
    storage = LocalStorage(root_dir=settings.storage_root)

    exec_repo = ExecutionRepository(db_session)
    know_repo = KnowledgeRepository(db_session)
    focus_repo = FocusRepository(db_session)
    src_repo = SourceRepository(db_session)
    pub_repo = PublishingRepository(db_session)
    quota_mgr = QuotaManager(exec_repo)

    class FailingLlm:
        async def extract(self, *_args: Any, **_kwargs: Any) -> Any:
            raise ConnectionError("Upstream LLM provider down")

        async def complete(self, *_args: Any, **_kwargs: Any) -> Any:
            raise ConnectionError("Upstream LLM provider down")

    from atlas.adapters.fakes.providers import (
        FakeEmbedder,
        FakeImageGenerator,
        FakeImageSearch,
        FakeNotifier,
        FakeRenderer,
        FakeSearch,
        FakeSoundLibrary,
        FakeSourceFetcher,
    )

    runner = PipelineRunner(
        execution_repo=exec_repo,
        knowledge_repo=know_repo,
        focus_repo=focus_repo,
        source_repo=src_repo,
        publishing_repo=pub_repo,
        storage=storage,
        llm=FailingLlm(),
        embedder=FakeEmbedder(),
        search=FakeSearch(),
        source_fetcher=FakeSourceFetcher(),
        image_search=FakeImageSearch(),
        image_gen=FakeImageGenerator(),
        sound_lib=FakeSoundLibrary(),
        renderer=FakeRenderer(storage),
        notifier=FakeNotifier(),
        quota_mgr=quota_mgr,
    )

    topic_id = f"topic_fail_{uuid.uuid4().hex[:8]}"
    await _seed_prerequisites(focus_repo, src_repo, topic_id)

    run_id = f"run_fail_{uuid.uuid4().hex[:8]}"
    now = utc_now()
    focus = FocusSnapshot(
        focus_id="focus_fail",
        scope_mode=ScopeMode.EXPLORATORY,
        facets=[],
        captured_at=now,
    )
    run = Run(
        id=run_id,
        topic_id=topic_id,
        channel_id="origins",
        status=RunStatus.PENDING,
        captured_focus=focus,
        trace_id="tr_fail",
        actor_id="operator",
        created_at=now,
        updated_at=now,
    )
    await exec_repo.create_run(run)

    with pytest.raises(StepExecutionError) as exc_info:
        await runner.run_pipeline(run_id)

    assert exc_info.value.step_name == PipelineStage.IDEA_DISCOVERY.value
    assert "Upstream LLM provider down" in exc_info.value.reason

    # Verify run and step state in database
    failed_run = await exec_repo.get_run(run_id)
    assert failed_run.status == RunStatus.FAILED
    assert "Upstream LLM provider down" in (failed_run.error or "")

    failed_step = await exec_repo.get_step(f"step_{run_id}_idea_discovery")
    assert failed_step.status.value == "failed"
    assert "Upstream LLM provider down" in (failed_step.error or "")


@pytest.mark.asyncio
async def test_sse_event_serialization() -> None:
    """P0-05: Server-Sent Events are serialized with json.dumps without injection vulnerability."""
    malicious_run_id = 'test_run"}\n\nevent: evil\ndata: {"hacked": true'
    events = []
    async for event_chunk in event_generator(malicious_run_id):
        events.append(event_chunk)

    assert len(events) >= 1
    chunk = events[0]
    assert chunk.startswith("data: ")
    raw_json = chunk[len("data: ") :].rstrip("\n")
    parsed = json.loads(raw_json)
    assert parsed["run_id"] == malicious_run_id
    assert parsed["event"] == "connected"
