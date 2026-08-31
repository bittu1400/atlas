"""FastAPI HTTP API Integration Tests with AsyncClient."""

from collections.abc import AsyncGenerator

import pytest
from atlas.adapters.persistence.repositories.execution_repository import ExecutionRepository
from atlas.adapters.persistence.repositories.focus_repository import FocusRepository
from atlas.adapters.persistence.repositories.knowledge_repository import KnowledgeRepository
from atlas.adapters.persistence.repositories.production_repository import ProductionRepository
from atlas.adapters.persistence.repositories.publishing_repository import PublishingRepository
from atlas.adapters.persistence.repositories.source_repository import SourceRepository
from atlas.adapters.storage.local import LocalStorage
from atlas.domain.focus.models import Domain, ResearchProfile
from atlas.domain.knowledge.models import Topic, TopicStatus
from atlas.domain.publishing.models import Channel
from atlas.platform.clock import utc_now
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
    from atlas.adapters.fakes.providers import (
        FakeEmbedder,
        FakeImageGenerator,
        FakeImageSearch,
        FakeLlm,
        FakeNotifier,
        FakePublisher,
        FakeQueueBroker,
        FakeRenderer,
        FakeSearch,
        FakeSoundLibrary,
        FakeSourceFetcher,
    )
    from atlas.application.pipeline.runner import PipelineRunner
    from atlas.platform.quota import QuotaManager

    from apps.api.dependencies import get_pipeline_runner, get_queue_broker

    app.dependency_overrides[get_queue_broker] = lambda: FakeQueueBroker()

    def override_get_pipeline_runner() -> PipelineRunner:
        return PipelineRunner(
            execution_repo=ExecutionRepository(db_session),
            knowledge_repo=KnowledgeRepository(db_session),
            focus_repo=FocusRepository(db_session),
            source_repo=SourceRepository(db_session),
            publishing_repo=PublishingRepository(db_session),
            production_repo=ProductionRepository(db_session),
            storage=test_storage,
            llm=FakeLlm(),
            embedder=FakeEmbedder(),
            search=FakeSearch(),
            source_fetcher=FakeSourceFetcher(),
            image_search=FakeImageSearch(),
            image_gen=FakeImageGenerator(),
            sound_lib=FakeSoundLibrary(),
            renderer=FakeRenderer(test_storage),
            notifier=FakeNotifier(),
            quota_mgr=QuotaManager(ExecutionRepository(db_session)),
            publisher=FakePublisher(),
        )

    app.dependency_overrides[get_pipeline_runner] = override_get_pipeline_runner

    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


async def _seed_api_topic(db_session: AsyncSession, topic_id: str) -> None:
    focus_repo = FocusRepository(db_session)
    src_repo = SourceRepository(db_session)
    pub_repo = PublishingRepository(db_session)

    domain = Domain(
        id="dom_science",
        name="Science",
        description="Science domain",
        research_profile=ResearchProfile(),
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
    channel = Channel(
        id="origins",
        name="Origins Channel",
        audience_timezone="UTC",
        style_profile={},
        created_at=utc_now(),
    )
    await pub_repo.save_channel(channel)


@pytest.mark.asyncio
async def test_health_check_endpoint(api_client: AsyncClient) -> None:
    """Verify GET /health returns 200 and healthy status."""
    response = await api_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "atlas-backend"


@pytest.mark.asyncio
async def test_quota_status_endpoint(api_client: AsyncClient) -> None:
    """Verify GET /quota returns provider token bucket info."""
    response = await api_client.get("/quota")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "providers" in data


@pytest.mark.asyncio
async def test_run_creation_and_inspection_flow(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Verify Run creation, list, step query, and gate inspection via API."""
    await _seed_api_topic(db_session, "topic_api_test_01")

    # 1. Create Run
    create_payload = {
        "topic_id": "topic_api_test_01",
        "channel_id": "origins",
        "actor_id": "api_user",
    }
    create_resp = await api_client.post("/runs", json=create_payload)
    assert create_resp.status_code == 201
    run_data = create_resp.json()
    run_id = run_data["id"]
    assert run_data["status"] == "suspended"  # Suspended at topic selection gate

    # 2. Get Run by ID
    get_resp = await api_client.get(f"/runs/{run_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == run_id

    # 3. List Runs
    list_resp = await api_client.get("/runs")
    assert list_resp.status_code == 200
    runs = list_resp.json()
    assert any(r["id"] == run_id for r in runs)

    # 4. List Steps for Run
    steps_resp = await api_client.get(f"/runs/{run_id}/steps")
    assert steps_resp.status_code == 200
    steps = steps_resp.json()
    assert len(steps) >= 1

    # 5. List Pending Gates
    pending_resp = await api_client.get("/gates/pending")
    assert pending_resp.status_code == 200
    pending_gates = pending_resp.json()
    assert len(pending_gates) == 1
    gate_id = pending_gates[0]["id"]

    # 6. Approve Gate via API
    approve_resp = await api_client.post(
        f"/gates/{gate_id}/approve", json={"actor_id": "api_operator"}
    )
    assert approve_resp.status_code == 200
    approval_data = approve_resp.json()
    assert approval_data["decision"] == "approved"

    # 7. Verify next gate suspended (Knowledge Object gate)
    pending_resp2 = await api_client.get("/gates/pending")
    assert len(pending_resp2.json()) == 1


@pytest.mark.asyncio
async def test_gate_rejection_flow_via_api(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Verify structured rejection through POST /gates/{gate_id}/reject."""
    await _seed_api_topic(db_session, "topic_api_reject")

    create_resp = await api_client.post(
        "/runs",
        json={"topic_id": "topic_api_reject", "channel_id": "origins"},
    )
    assert create_resp.status_code == 201
    run_id = create_resp.json()["id"]

    pending_gates = (await api_client.get("/gates/pending")).json()
    gate_id = pending_gates[0]["id"]

    reject_payload = {
        "target_ref": "topic_api_reject",
        "rubric_dimension": "novelty",
        "reason": "Angle is too similar to recent release.",
        "action": "regenerate",
        "actor_id": "operator_dan",
    }
    reject_resp = await api_client.post(f"/gates/{gate_id}/reject", json=reject_payload)
    assert reject_resp.status_code == 200
    reject_data = reject_resp.json()
    assert reject_data["decision"] == "rejected"
    assert reject_data["feedback"]["reason"] == "Angle is too similar to recent release."

    # Run is in reworking state
    run_status = (await api_client.get(f"/runs/{run_id}")).json()["status"]
    assert run_status == "reworking"
