"""Local filesystem content-addressed blob storage adapter.

Stores blobs at `var/blobs/sha256/ab/cd/<hash>` to avoid filesystem directory bloat
and enable zero-cost deduplication.
"""

import asyncio
import hashlib
import os
import re
import tempfile
from pathlib import Path


class LocalStorage:
    """Local filesystem content-addressed storage adapter."""

    KEY_PATTERN = re.compile(r"^sha256/[0-9a-f]{2}/[0-9a-f]{2}/[0-9a-f]{64}$")

    def __init__(self, root_dir: str = "var/blobs") -> None:
        self.root_path = Path(root_dir).resolve()
        self.root_path.mkdir(parents=True, exist_ok=True)

    def _sync_put(self, content: bytes, content_hash: str) -> str:
        sub1 = content_hash[:2]
        sub2 = content_hash[2:4]

        target_dir = self.root_path / "sha256" / sub1 / sub2
        target_dir.mkdir(parents=True, exist_ok=True)

        target_file = target_dir / content_hash
        if not target_file.exists():
            fd, temp_path = tempfile.mkstemp(dir=target_dir)
            try:
                with os.fdopen(fd, "wb") as f:
                    f.write(content)
                os.replace(temp_path, target_file)
            except Exception:
                os.unlink(temp_path)
                raise

        return f"sha256/{sub1}/{sub2}/{content_hash}"

    async def put(
        self,
        content: bytes,
        mime_type: str = "application/octet-stream",  # noqa: ARG002
    ) -> str:
        """Store bytes content-addressed by SHA-256 and return storage key."""
        content_hash = hashlib.sha256(content).hexdigest()
        return await asyncio.to_thread(self._sync_put, content, content_hash)

    def _validate_key(self, storage_key: str) -> Path:
        if not self.KEY_PATTERN.match(storage_key):
            raise ValueError(f"Invalid storage key format: '{storage_key}'")
        target_file = (self.root_path / storage_key).resolve()
        if not str(target_file).startswith(str(self.root_path)):
            raise ValueError("Path traversal detected")
        return target_file

    def _sync_get(self, storage_key: str) -> bytes:
        target_file = self._validate_key(storage_key)
        if not target_file.exists():
            raise FileNotFoundError(f"Blob with key '{storage_key}' not found")
        return target_file.read_bytes()

    async def get(self, storage_key: str) -> bytes:
        """Retrieve stored bytes by key."""
        return await asyncio.to_thread(self._sync_get, storage_key)

    def _sync_exists(self, storage_key: str) -> bool:
        target_file = self._validate_key(storage_key)
        return target_file.exists()

    async def exists(self, storage_key: str) -> bool:
        """Check if blob exists in storage."""
        return await asyncio.to_thread(self._sync_exists, storage_key)
