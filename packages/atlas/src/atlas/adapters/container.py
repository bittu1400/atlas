"""Unified production dependency injection container.

Wires the concrete adapters the entrypoints (API, worker, CLI) run against.
Nothing from `adapters/fakes/` is imported here: rule R2 keeps fakes in the
tests, and a production container that resolves a provider port to a fake makes
every "the pipeline ran" claim meaningless.
"""

from functools import cached_property

from atlas.adapters.audio.freesound import FreesoundLibrary
from atlas.adapters.audio.speech import NoOpSpeech
from atlas.adapters.images.archive_org import InternetArchiveSearch
from atlas.adapters.images.composite import CompositeImageSearch
from atlas.adapters.images.stub_generator import StubImageGenerator
from atlas.adapters.images.wikimedia import WikimediaCommonsSearch
from atlas.adapters.llm.gemini import GeminiLlm
from atlas.adapters.llm.ollama import OllamaEmbedder
from atlas.adapters.notify.logging_notifier import LoggingNotifier
from atlas.adapters.persistence.repositories.execution_repository import ExecutionRepository
from atlas.adapters.persistence.repositories.focus_repository import FocusRepository
from atlas.adapters.persistence.repositories.knowledge_repository import KnowledgeRepository
from atlas.adapters.persistence.repositories.production_repository import ProductionRepository
from atlas.adapters.persistence.repositories.publishing_repository import PublishingRepository
from atlas.adapters.persistence.repositories.source_repository import SourceRepository
from atlas.adapters.publish.stub import StubPublisher
from atlas.adapters.queue.dramatiq_broker import DramatiqQueueBroker
from atlas.adapters.renderer.stub import StubRenderer
from atlas.adapters.search.wikipedia import WikipediaSearch
from atlas.adapters.sources.fetcher import HttpSourceFetcher
from atlas.adapters.storage.local import LocalStorage
from atlas.application.pipeline.runner import PipelineRunner
from atlas.platform.config import get_settings
from atlas.platform.errors import AtlasError
from atlas.platform.quota import QuotaManager
from sqlalchemy.ext.asyncio import AsyncSession


class SessionRequiredError(AtlasError):
    """Raised when a database-backed dependency is requested from a sessionless container."""

    def __init__(self, dependency: str) -> None:
        super().__init__(f"A database session is required to build '{dependency}'")
        self.dependency = dependency


class MissingProviderCredentialError(AtlasError):
    """Raised when a provider adapter is built without the credential it needs.

    Failing at container construction beats failing eight stages later with an
    opaque 401 from the provider.
    """

    def __init__(self, variable_name: str) -> None:
        super().__init__(f"Environment variable '{variable_name}' is required but not set")
        self.variable_name = variable_name


def _require_credential(value: str | None, variable_name: str) -> str:
    """Return a configured credential or name the variable that is missing.

    The value comes from `Settings`, which reads `.env` as well as the process
    environment; a raw `os.getenv` never saw `.env` at all (defect V-06).
    """
    if not value:
        raise MissingProviderCredentialError(variable_name)
    return value


class Container:
    """Unified Dependency Injection Container for Production."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        self.session = session
        self.settings = get_settings()
        settings = self.settings
        self.storage = LocalStorage(root_dir=settings.storage_root)

        self.embedder = OllamaEmbedder(base_url=settings.ollama_base_url)
        self.image_search = CompositeImageSearch(
            [WikimediaCommonsSearch(), InternetArchiveSearch()]
        )
        self.image_gen = StubImageGenerator()
        self.speech = NoOpSpeech()
        self.queue_broker = DramatiqQueueBroker()
        self.search = WikipediaSearch()
        self.source_fetcher = HttpSourceFetcher()
        self.notifier = LoggingNotifier()

        # Stubs: named for what they are, not for what they stand in for (R3).
        # Real rendering and real publishing do not exist yet — see docs/STATUS.md.
        self.renderer = StubRenderer(self.storage)
        self.publisher = StubPublisher()

        # Repositories
        if self.session:
            self.execution_repo: ExecutionRepository | None = ExecutionRepository(self.session)
            self.knowledge_repo: KnowledgeRepository | None = KnowledgeRepository(self.session)
            self.focus_repo: FocusRepository | None = FocusRepository(self.session)
            self.source_repo: SourceRepository | None = SourceRepository(self.session)
            self.publishing_repo: PublishingRepository | None = PublishingRepository(self.session)
            self.production_repo: ProductionRepository | None = ProductionRepository(self.session)
            self.quota_mgr: QuotaManager | None = QuotaManager(self.execution_repo)
        else:
            self.execution_repo = None
            self.knowledge_repo = None
            self.focus_repo = None
            self.source_repo = None
            self.publishing_repo = None
            self.production_repo = None
            self.quota_mgr = None

    @cached_property
    def llm(self) -> GeminiLlm:
        """Tier 2 hosted LLM. Built on first use so credential-free commands still run."""
        return GeminiLlm(
            api_key=_require_credential(self.settings.gemini_api_key, "GEMINI_API_KEY")
        )

    @cached_property
    def sound_lib(self) -> FreesoundLibrary:
        """CC0 sound library. Built on first use so credential-free commands still run."""
        return FreesoundLibrary(
            api_key=_require_credential(self.settings.freesound_api_key, "FREESOUND_API_KEY")
        )

    def require_execution_repo(self) -> ExecutionRepository:
        """Return the execution repository, or fail if this container has no session."""
        if self.execution_repo is None:
            raise SessionRequiredError("ExecutionRepository")
        return self.execution_repo

    def require_focus_repo(self) -> FocusRepository:
        """Return the focus repository, or fail if this container has no session."""
        if self.focus_repo is None:
            raise SessionRequiredError("FocusRepository")
        return self.focus_repo

    def require_source_repo(self) -> SourceRepository:
        """Return the source repository, or fail if this container has no session."""
        if self.source_repo is None:
            raise SessionRequiredError("SourceRepository")
        return self.source_repo

    def require_publishing_repo(self) -> PublishingRepository:
        """Return the publishing repository, or fail if this container has no session."""
        if self.publishing_repo is None:
            raise SessionRequiredError("PublishingRepository")
        return self.publishing_repo

    def get_pipeline_runner(self) -> PipelineRunner:
        """Build the pipeline runner; requires a database session."""
        if (
            self.execution_repo is None
            or self.knowledge_repo is None
            or self.focus_repo is None
            or self.source_repo is None
            or self.publishing_repo is None
            or self.production_repo is None
            or self.quota_mgr is None
        ):
            raise SessionRequiredError("PipelineRunner")
        return PipelineRunner(
            execution_repo=self.execution_repo,
            knowledge_repo=self.knowledge_repo,
            focus_repo=self.focus_repo,
            source_repo=self.source_repo,
            publishing_repo=self.publishing_repo,
            production_repo=self.production_repo,
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
