"""Research Agent for discovering and snapshotting Tier 0 primary sources."""

from dataclasses import dataclass

from atlas.application.ports.repositories import SourceRepositoryPort
from atlas.application.ports.search import Search, SearchResultItem
from atlas.application.ports.sources import SourceFetcher
from atlas.application.ports.storage import Storage
from atlas.domain.common.enums import SourceTier
from atlas.domain.knowledge.models import Snapshot, Source
from atlas.platform.clock import utc_now
from atlas.platform.ids import generate_snapshot_id, generate_source_id
from atlas.platform.logging import get_logger
from pydantic import HttpUrl

logger = get_logger("application.agents.research")


@dataclass(frozen=True)
class ResearchResult:
    """Outcome of research agent execution for a topic."""

    topic_id: str
    sources_discovered: int
    snapshots_created: list[str]


class ResearchAgent:
    """Agent that searches for Tier 0 primary literature and archives, taking content-addressed snapshots."""

    def __init__(
        self,
        search: Search,
        source_fetcher: SourceFetcher,
        storage: Storage,
        source_repo: SourceRepositoryPort,
    ) -> None:
        self.search = search
        self.source_fetcher = source_fetcher
        self.storage = storage
        self.source_repo = source_repo

    async def execute(self, topic_id: str, search_query: str, limit: int = 3) -> ResearchResult:
        """Discover primary sources for the topic and persist immutable snapshots."""
        logger.info("research.start", topic_id=topic_id, query=search_query)

        # 1. Search Tier 0 sources
        search_hits: list[SearchResultItem] = await self.search.search(
            query=search_query, limit=limit
        )
        if not search_hits:
            logger.warning("research.no_hits", topic_id=topic_id, query=search_query)
            # Fallback direct target url for topic archive
            search_hits = [
                SearchResultItem(
                    title=f"Archival Record for {topic_id}",
                    url=f"https://en.wikipedia.org/wiki/{topic_id.replace(' ', '_')}",
                    snippet=f"Primary encyclopedic source for {topic_id}.",
                    source_name="Wikipedia",
                )
            ]

        snapshot_ids: list[str] = []

        # 2. Fetch and snapshot each discovered source
        for hit in search_hits:
            try:
                content_bytes, chash, mime_type = await self.source_fetcher.fetch(hit.url)
                blob_key = await self.storage.put(content_bytes, mime_type)

                # Persist Source
                source = Source(
                    id=generate_source_id(),
                    title=hit.title,
                    url=HttpUrl(hit.url),
                    author=hit.source_name,
                    source_tier=SourceTier.PRIMARY,
                    created_at=utc_now(),
                )
                await self.source_repo.save_source(source)

                # Persist Snapshot
                snapshot = Snapshot(
                    id=generate_snapshot_id(),
                    source_id=source.id,
                    content_hash=chash,
                    storage_key=blob_key,
                    byte_size=len(content_bytes),
                    mime_type=mime_type,
                    retrieved_at=utc_now(),
                )
                await self.source_repo.save_snapshot(snapshot)
                snapshot_ids.append(snapshot.id)

                logger.info(
                    "research.snapshot_saved",
                    source_id=source.id,
                    snapshot_id=snapshot.id,
                    bytes=len(content_bytes),
                )
            except Exception as exc:
                logger.error("research.source_fetch_failed", url=hit.url, error=str(exc))
                continue

        return ResearchResult(
            topic_id=topic_id,
            sources_discovered=len(search_hits),
            snapshots_created=snapshot_ids,
        )
