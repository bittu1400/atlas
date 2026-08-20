"""Integration tests for LocalStorage content-addressed blob storage."""

import hashlib
from pathlib import Path

import pytest
from atlas.adapters.storage.local import LocalStorage


@pytest.mark.asyncio
async def test_content_addressed_storage(tmp_path: Path) -> None:
    """Verify storing bytes content-addressed by SHA-256 and retrieving by key."""
    storage = LocalStorage(root_dir=str(tmp_path / "blobs"))

    sample_content = b"Knowledge is the product. Every renderer is downstream of it."
    expected_hash = hashlib.sha256(sample_content).hexdigest()

    # 1. Put content
    storage_key = await storage.put(sample_content, mime_type="text/plain")
    assert storage_key == f"sha256/{expected_hash[:2]}/{expected_hash[2:4]}/{expected_hash}"

    # 2. Check existence
    assert await storage.exists(storage_key) is True

    # 3. Retrieve content
    retrieved_bytes = await storage.get(storage_key)
    assert retrieved_bytes == sample_content

    # 4. Duplicate put produces identical storage key without error
    key2 = await storage.put(sample_content, mime_type="text/plain")
    assert key2 == storage_key
