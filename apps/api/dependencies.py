from collections.abc import AsyncGenerator

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
    FakeSpeech,
)
from atlas.adapters.persistence.database import get_session_manager
from atlas.adapters.persistence.repositories.execution_repository import ExecutionRepository
from atlas.adapters.persistence.repositories.focus_repository import FocusRepository
from atlas.adapters.persistence.repositories.knowledge_repository import KnowledgeRepository
from atlas.adapters.persistence.repositories.publishing_repository import PublishingRepository
from atlas.adapters.persistence.repositories.source_repository import SourceRepository
from atlas.adapters.storage.local import LocalStorage
from atlas.application.pipeline.runner import PipelineRunner
from atlas.application.ports.publish import Publisher
from atlas.application.ports.speech import Speech
from atlas.application.ports.storage import Storage
from atlas.application.usecases.approve_gate import ApproveGateUseCase
from atlas.application.usecases.create_run import CreateRunUseCase
from atlas.application.usecases.get_run_status import (
    GetQuotaStatusUseCase,
    GetRunStatusUseCase,
    ListGatesUseCase,
    ListRunsUseCase,
)
from atlas.application.usecases.reject_gate import RejectGateUseCase
from atlas.platform.config import get_settings
from atlas.platform.quota import QuotaManager
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    api_key: str | None = Security(api_key_header),
) -> str:
    """Verify incoming API key if authentication is enabled in Settings."""
    settings = get_settings()
    if settings.api_auth_enabled and (
        not api_key or (settings.api_key and api_key != settings.api_key)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Invalid or missing API Key",
        )
    return api_key or "anonymous"


async def get_db_session() -> AsyncGenerator[AsyncSession]:
    """Yield database session for request lifecycle."""
    session_manager = get_session_manager()
    async with session_manager.session() as session:
        yield session


def get_storage() -> Storage:
    """Return configured content-addressed storage adapter."""
    settings = get_settings()
    return LocalStorage(root_dir=settings.storage_root)


def get_execution_repository(
    session: AsyncSession = Depends(get_db_session),
) -> ExecutionRepository:
    return ExecutionRepository(session)


def get_focus_repository(session: AsyncSession = Depends(get_db_session)) -> FocusRepository:
    return FocusRepository(session)


def get_knowledge_repository(
    session: AsyncSession = Depends(get_db_session),
) -> KnowledgeRepository:
    return KnowledgeRepository(session)


def get_source_repository(session: AsyncSession = Depends(get_db_session)) -> SourceRepository:
    return SourceRepository(session)


def get_publishing_repository(
    session: AsyncSession = Depends(get_db_session),
) -> PublishingRepository:
    return PublishingRepository(session)


# Global fakes singletons for testing / mock pipeline runs
_fake_queue_broker = FakeQueueBroker()
_fake_notifier = FakeNotifier()
_fake_llm = FakeLlm()
_fake_embedder = FakeEmbedder()
_fake_search = FakeSearch()
_fake_source_fetcher = FakeSourceFetcher()
_fake_image_search = FakeImageSearch()
_fake_image_gen = FakeImageGenerator()
_fake_sound_lib = FakeSoundLibrary()
_fake_publisher = FakePublisher()
_fake_speech = FakeSpeech()


def get_queue_broker() -> FakeQueueBroker:
    return _fake_queue_broker


def get_publisher() -> Publisher:
    return _fake_publisher


def get_speech() -> Speech:
    return _fake_speech


def get_pipeline_runner(
    execution_repo: ExecutionRepository = Depends(get_execution_repository),
    knowledge_repo: KnowledgeRepository = Depends(get_knowledge_repository),
    focus_repo: FocusRepository = Depends(get_focus_repository),
    source_repo: SourceRepository = Depends(get_source_repository),
    publishing_repo: PublishingRepository = Depends(get_publishing_repository),
    storage: Storage = Depends(get_storage),
    publisher: Publisher = Depends(get_publisher),
) -> PipelineRunner:
    quota_mgr = QuotaManager(execution_repo=execution_repo)
    renderer = FakeRenderer(storage=storage)

    return PipelineRunner(
        execution_repo=execution_repo,
        knowledge_repo=knowledge_repo,
        focus_repo=focus_repo,
        source_repo=source_repo,
        publishing_repo=publishing_repo,
        storage=storage,
        llm=_fake_llm,
        embedder=_fake_embedder,
        search=_fake_search,
        source_fetcher=_fake_source_fetcher,
        image_search=_fake_image_search,
        image_gen=_fake_image_gen,
        sound_lib=_fake_sound_lib,
        renderer=renderer,
        notifier=_fake_notifier,
        quota_mgr=quota_mgr,
        publisher=publisher,
    )


def get_create_run_use_case(
    execution_repo: ExecutionRepository = Depends(get_execution_repository),
    focus_repo: FocusRepository = Depends(get_focus_repository),
    queue_broker: FakeQueueBroker = Depends(get_queue_broker),
) -> CreateRunUseCase:
    return CreateRunUseCase(execution_repo, focus_repo, queue_broker)


def get_approve_gate_use_case(
    execution_repo: ExecutionRepository = Depends(get_execution_repository),
    queue_broker: FakeQueueBroker = Depends(get_queue_broker),
) -> ApproveGateUseCase:
    return ApproveGateUseCase(execution_repo, queue_broker)


def get_reject_gate_use_case(
    execution_repo: ExecutionRepository = Depends(get_execution_repository),
    queue_broker: FakeQueueBroker = Depends(get_queue_broker),
) -> RejectGateUseCase:
    return RejectGateUseCase(execution_repo, queue_broker)


def get_run_status_use_case(
    execution_repo: ExecutionRepository = Depends(get_execution_repository),
) -> GetRunStatusUseCase:
    return GetRunStatusUseCase(execution_repo)


def get_list_runs_use_case(
    execution_repo: ExecutionRepository = Depends(get_execution_repository),
) -> ListRunsUseCase:
    return ListRunsUseCase(execution_repo)


def get_list_gates_use_case(
    execution_repo: ExecutionRepository = Depends(get_execution_repository),
) -> ListGatesUseCase:
    return ListGatesUseCase(execution_repo)


def get_quota_status_use_case(
    execution_repo: ExecutionRepository = Depends(get_execution_repository),
) -> GetQuotaStatusUseCase:
    return GetQuotaStatusUseCase(execution_repo)
