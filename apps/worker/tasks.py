from atlas.adapters.fakes.providers import (
    FakeEmbedder,
    FakeImageGenerator,
    FakeImageSearch,
    FakeLlm,
    FakeNotifier,
    FakePublisher,
    FakeRenderer,
    FakeSearch,
    FakeSoundLibrary,
    FakeSourceFetcher,
)
from atlas.adapters.persistence.database import get_session_manager
from atlas.adapters.persistence.repositories.execution_repository import ExecutionRepository
from atlas.adapters.persistence.repositories.focus_repository import FocusRepository
from atlas.adapters.persistence.repositories.knowledge_repository import KnowledgeRepository
from atlas.adapters.persistence.repositories.publishing_repository import PublishingRepository
from atlas.adapters.persistence.repositories.source_repository import SourceRepository
from atlas.adapters.storage.local import LocalStorage
from atlas.application.pipeline.runner import PipelineRunner
from atlas.platform.config import get_settings
from atlas.platform.logging import get_logger
from atlas.platform.quota import QuotaManager

logger = get_logger("apps.worker.tasks")


async def execute_pipeline_task(run_id: str) -> None:
    """Background worker task executing pipeline stages for a Run."""
    logger.info("worker.task_started", run_id=run_id)
    session_manager = get_session_manager()

    async with session_manager.session() as session:
        settings = get_settings()
        storage = LocalStorage(root_dir=settings.storage_root)

        exec_repo = ExecutionRepository(session)
        know_repo = KnowledgeRepository(session)
        focus_repo = FocusRepository(session)
        src_repo = SourceRepository(session)
        pub_repo = PublishingRepository(session)

        quota_mgr = QuotaManager(exec_repo)
        renderer = FakeRenderer(storage)
        publisher = FakePublisher()

        runner = PipelineRunner(
            execution_repo=exec_repo,
            knowledge_repo=know_repo,
            focus_repo=focus_repo,
            source_repo=src_repo,
            publishing_repo=pub_repo,
            storage=storage,
            llm=FakeLlm(),
            embedder=FakeEmbedder(),
            search=FakeSearch(),
            source_fetcher=FakeSourceFetcher(),
            image_search=FakeImageSearch(),
            image_gen=FakeImageGenerator(),
            sound_lib=FakeSoundLibrary(),
            renderer=renderer,
            notifier=FakeNotifier(),
            quota_mgr=quota_mgr,
            publisher=publisher,
        )

        await runner.run_pipeline(run_id)
        logger.info("worker.task_finished", run_id=run_id)
