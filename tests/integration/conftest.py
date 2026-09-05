"""Fixtures shared by the integration suites that drive the HTTP app.

`api_client` wires the real FastAPI app against the test session and the fake
providers. It lives here rather than in one test module because two suites now
exercise the same app, and a second copy of this wiring is free to drift from
the one the other suite asserts against.
"""

from collections.abc import AsyncGenerator

import pytest
from atlas.adapters.persistence.repositories.execution_repository import ExecutionRepository
from atlas.adapters.persistence.repositories.focus_repository import FocusRepository
from atlas.adapters.persistence.repositories.knowledge_repository import KnowledgeRepository
from atlas.adapters.persistence.repositories.production_repository import ProductionRepository
from atlas.adapters.persistence.repositories.publishing_repository import PublishingRepository
from atlas.adapters.persistence.repositories.source_repository import SourceRepository
from atlas.adapters.storage.local import LocalStorage
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
