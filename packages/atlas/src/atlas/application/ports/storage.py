"""Storage port interface for content-addressed blob storage."""

from typing import Protocol


class Storage(Protocol):
    """Port interface for storing and retrieving content-addressed blobs."""

    async def put(self, content: bytes, mime_type: str = "application/octet-stream") -> str:
        """Store bytes content-addressed by SHA-256 hash and return storage key."""
        ...

    async def get(self, storage_key: str) -> bytes:
        """Retrieve bytes by storage key."""
        ...

    async def exists(self, storage_key: str) -> bool:
        """Check if storage key exists."""
        ...
