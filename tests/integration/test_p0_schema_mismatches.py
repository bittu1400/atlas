"""Regression tests for Phase 2 P0 issues (A-01 to A-05)."""

import tempfile
from pathlib import Path

import pytest
from atlas.adapters.storage.local import LocalStorage
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_a01_scope_mode_schema_mismatch(db_session: AsyncSession) -> None:
    """A-01: ScopeMode schema mismatch.
    DB should accept 'hard' and 'exploratory'.
    """
    await db_session.execute(
        text(
            """
            INSERT INTO focus (id, name, scope_mode, facets, actor_id, created_at)
            VALUES ('foc_hard', 'Test Hard Focus', 'hard', '[]', 'actor1', now())
            """
        )
    )
    await db_session.commit()

    # DB should reject 'strict' since it's not in the enum
    with pytest.raises(Exception, match=".*"):
        await db_session.execute(
            text(
                """
                INSERT INTO focus (id, name, scope_mode, facets, actor_id, created_at)
                VALUES ('foc_strict', 'Test Strict', 'strict', '[]', 'actor1', now())
                """
            )
        )
        await db_session.commit()


@pytest.mark.asyncio
async def test_a02_source_tier_schema_mismatch(db_session: AsyncSession) -> None:
    """A-02: SourceTier schema mismatch. DB should accept 'reference' and 'unvetted'."""
    await db_session.execute(
        text(
            """
            INSERT INTO sources (id, url, title, source_tier, created_at)
            VALUES ('src_test_ref', 'http://ref', 'Ref', 'reference', now())
            """
        )
    )
    await db_session.commit()

    with pytest.raises(Exception, match=".*"):
        await db_session.execute(
            text(
                """
                INSERT INTO sources (id, url, title, source_tier, created_at)
                VALUES ('src_test_bad', 'http://bad', 'Bad', 'journalistic', now())
                """
            )
        )
        await db_session.commit()


@pytest.mark.asyncio
async def test_a03_local_storage_path_traversal() -> None:
    """A-03: Local storage path traversal / arbitrary local-file reads."""
    with tempfile.TemporaryDirectory() as td:
        storage = LocalStorage(root_dir=td)
        # Setup a dummy file outside storage
        outside_file = Path(td) / "secret.txt"
        outside_file.write_text("secret")

        # Try to read it using traversal
        with pytest.raises(ValueError):
            await storage.get("../secret.txt")

        # Try to read using absolute path
        with pytest.raises(ValueError):
            await storage.get(str(outside_file.absolute()))

        # Try to read arbitrary bad key
        with pytest.raises(ValueError):
            await storage.get("sha256/xx/yy/zz")


@pytest.mark.asyncio
async def test_a04_false_traceability_chain(db_session: AsyncSession) -> None:
    """A-04: False traceability chain is database-permitted."""
    # Source A and B
    await db_session.execute(
        text(
            "INSERT INTO sources (id, url, title, source_tier, created_at) VALUES ('src_a', 'http://a', 'A', 'primary', now())"
        )
    )
    await db_session.execute(
        text(
            "INSERT INTO sources (id, url, title, source_tier, created_at) VALUES ('src_b', 'http://b', 'B', 'primary', now())"
        )
    )

    # Snapshot for A
    await db_session.execute(
        text(
            "INSERT INTO snapshots (id, source_id, content_hash, storage_key, mime_type, byte_size, retrieved_at) VALUES ('snap_1', 'src_a', 'hash1', 'sha256/ha/sh/hash1', 'text/html', 10, now())"
        )
    )
    await db_session.commit()

    # Evidence for B but referencing Snapshot A
    with pytest.raises(Exception, match=".*"):
        await db_session.execute(
            text(
                "INSERT INTO evidence (id, source_id, snapshot_id, locator, quote, stance, confidence, extracted_at) VALUES ('ev_1', 'src_b', 'snap_1', 'loc', 'quote', 'supports', 1.0, now())"
            )
        )
        await db_session.commit()


@pytest.mark.asyncio
async def test_a05_append_only_not_enforced(db_session: AsyncSession) -> None:
    """A-05: Append-only is not enforced. Topics cannot be deleted, sources cannot be updated."""
    await db_session.execute(
        text(
            "INSERT INTO domains (id, name, description, research_profile) VALUES ('dom_test', 'test', 'test', '{}')"
        )
    )
    await db_session.execute(
        text(
            "INSERT INTO topics (id, title, domain_id, status, created_at) VALUES ('top_1', 'Original', 'dom_test', 'proposed', now())"
        )
    )
    await db_session.execute(
        text(
            "INSERT INTO sources (id, url, title, source_tier, created_at) VALUES ('src_test', 'http', 'title', 'primary', now())"
        )
    )
    await db_session.commit()

    # Attempt to delete topic should fail
    with pytest.raises(Exception, match=".*"):
        await db_session.execute(text("DELETE FROM topics WHERE id = 'top_1'"))
        await db_session.commit()

    # Attempt to update source should fail
    with pytest.raises(Exception, match=".*"):
        await db_session.execute(text("UPDATE sources SET title = 'Changed' WHERE id = 'src_test'"))
        await db_session.commit()
