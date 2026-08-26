import os

from atlas.adapters.audio.freesound import FreesoundLibrary
from atlas.adapters.audio.speech import NoOpSpeech
from atlas.adapters.fakes.providers import (
    FakeNotifier,
    FakeSearch,
    FakeSourceFetcher,
)
from atlas.adapters.images.archive_org import InternetArchiveSearch
from atlas.adapters.images.composite import CompositeImageSearch
from atlas.adapters.images.local_sd import LocalStableDiffusionGenerator
from atlas.adapters.images.wikimedia import WikimediaCommonsSearch
from atlas.adapters.llm.gemini import GeminiLlm
from atlas.adapters.llm.ollama import OllamaEmbedder
from atlas.adapters.persistence.repositories.execution_repository import ExecutionRepository
from atlas.adapters.persistence.repositories.focus_repository import FocusRepository
from atlas.adapters.persistence.repositories.knowledge_repository import KnowledgeRepository
from atlas.adapters.persistence.repositories.publishing_repository import PublishingRepository
from atlas.adapters.persistence.repositories.source_repository import SourceRepository
from atlas.adapters.queue.dramatiq_broker import DramatiqQueueBroker
from atlas.adapters.storage.local import LocalStorage
from atlas.application.pipeline.runner import PipelineRunner
from atlas.platform.config import get_settings
from atlas.platform.quota import QuotaManager
from sqlalchemy.ext.asyncio import AsyncSession


class Container:
    """Unified Dependency Injection Container for Production."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        self.session = session
        settings = get_settings()
        self.storage = LocalStorage(root_dir=settings.storage_root)

        # Core Adapters
        self.llm = GeminiLlm(api_key=os.getenv("GEMINI_API_KEY", "dummy_key"))
        self.embedder = OllamaEmbedder(base_url="http://localhost:11434")
        self.image_search = CompositeImageSearch(
            [WikimediaCommonsSearch(), InternetArchiveSearch()]
        )
        self.image_gen = LocalStableDiffusionGenerator()
        self.sound_lib = FreesoundLibrary(api_key=os.getenv("FREESOUND_API_KEY", "dummy_key"))
        self.speech = NoOpSpeech()
        self.queue_broker = DramatiqQueueBroker()

        # Phase 7, 8, 9 Stubs
        self.search = FakeSearch()
        self.source_fetcher = FakeSourceFetcher()
        self.notifier = FakeNotifier()

        from atlas.adapters.publish.youtube import YouTubePublisher
        from atlas.adapters.renderer.remotion import RemotionRenderer

        self.renderer = RemotionRenderer(self.storage)
        self.publisher = YouTubePublisher()

        # Repositories
        if self.session:
            self.execution_repo = ExecutionRepository(self.session)
            self.knowledge_repo = KnowledgeRepository(self.session)
            self.focus_repo = FocusRepository(self.session)
            self.source_repo = SourceRepository(self.session)
            self.publishing_repo = PublishingRepository(self.session)
            self.quota_mgr = QuotaManager(self.execution_repo)
        else:
            self.execution_repo = None
            self.knowledge_repo = None
            self.focus_repo = None
            self.source_repo = None
            self.publishing_repo = None
            self.quota_mgr = None

    def get_pipeline_runner(self) -> PipelineRunner:
        if not self.session:
            raise ValueError("Database session required to build PipelineRunner")
        return PipelineRunner(
            execution_repo=self.execution_repo,
            knowledge_repo=self.knowledge_repo,
            focus_repo=self.focus_repo,
            source_repo=self.source_repo,
            publishing_repo=self.publishing_repo,
            storage=self.storage,
            llm=self.llm,
            embedder=self.embedder,
            search=self.search,
            source_fetcher=self.source_fetcher,
            image_search=self.image_search,
            image_gen=self.image_gen,
            sound_lib=self.sound_lib,
            renderer=self.renderer,
            notifier=self.notifier,
            quota_mgr=self.quota_mgr,
            publisher=self.publisher,
        )
