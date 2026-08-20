"""Port interface for polite source fetching and snapshotting."""

from typing import Protocol


class SourceFetcher(Protocol):
    """Port for fetching raw bytes from a source URL with polite throttling."""

    async def fetch(self, url: str) -> tuple[bytes, str, str]:
        """Fetch URL content, returning (content_bytes, sha256_hash, mime_type)."""
        ...
