from collections.abc import AsyncGenerator

from atlas.adapters.container import Container
from atlas.adapters.persistence.database import get_session_manager
from atlas.adapters.persistence.repositories.execution_repository import ExecutionRepository
from atlas.adapters.persistence.repositories.focus_repository import FocusRepository
from atlas.adapters.persistence.repositories.knowledge_repository import KnowledgeRepository
from atlas.adapters.persistence.repositories.publishing_repository import PublishingRepository
from atlas.adapters.persistence.repositories.source_repository import SourceRepository
from atlas.adapters.storage.local import LocalStorage
from atlas.application.pipeline.runner import PipelineRunner
from atlas.application.ports.publish import Publisher
from atlas.application.ports.queue import QueueBroker
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
from atlas.application.usecases.inspect_run import (
    GetRunKnowledgeUseCase,
    GetRunTelemetryUseCase,
)
from atlas.application.usecases.reject_gate import RejectGateUseCase
from atlas.platform.config import get_settings
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


def get_queue_broker() -> QueueBroker:
    # Just a placeholder if we need queue_broker directly
    return Container().queue_broker


def get_publisher() -> Publisher:
    return Container().publisher


def get_speech() -> Speech:
    return Container().speech


def get_pipeline_runner(session: AsyncSession = Depends(get_db_session)) -> PipelineRunner:
    return Container(session).get_pipeline_runner()


def get_create_run_use_case(
    execution_repo: ExecutionRepository = Depends(get_execution_repository),
    focus_repo: FocusRepository = Depends(get_focus_repository),
    queue_broker: QueueBroker = Depends(get_queue_broker),
) -> CreateRunUseCase:
    return CreateRunUseCase(execution_repo, focus_repo, queue_broker)


def get_approve_gate_use_case(
    execution_repo: ExecutionRepository = Depends(get_execution_repository),
    queue_broker: QueueBroker = Depends(get_queue_broker),
) -> ApproveGateUseCase:
    return ApproveGateUseCase(execution_repo, queue_broker)


def get_reject_gate_use_case(
    execution_repo: ExecutionRepository = Depends(get_execution_repository),
    queue_broker: QueueBroker = Depends(get_queue_broker),
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


def get_run_knowledge_use_case(
    execution_repo: ExecutionRepository = Depends(get_execution_repository),
    knowledge_repo: KnowledgeRepository = Depends(get_knowledge_repository),
) -> GetRunKnowledgeUseCase:
    return GetRunKnowledgeUseCase(execution_repo, knowledge_repo)


def get_run_telemetry_use_case(
    execution_repo: ExecutionRepository = Depends(get_execution_repository),
) -> GetRunTelemetryUseCase:
    return GetRunTelemetryUseCase(execution_repo)
