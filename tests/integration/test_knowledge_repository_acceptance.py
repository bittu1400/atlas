"""Acceptance Criteria Integration Tests for Knowledge System and Traceability.

Acceptance criterion (docs/STATUS.md & docs/SPEC.md):
A Knowledge Object can be written, revised, and read back at any prior version,
with the traceability chain enforced by foreign keys rather than by application code.
"""

import hashlib
from datetime import UTC, date, datetime

import pytest
from atlas.adapters.persistence.repositories.knowledge_repository import KnowledgeRepository
from atlas.adapters.persistence.repositories.source_repository import SourceRepository
from atlas.domain.common.enums import SourceTier
from atlas.domain.knowledge.models import (
    AssertionType,
    Claim,
    ClaimEvidenceLink,
    ClaimStatus,
    ClaimUsage,
    Evidence,
    EvidenceStance,
    KnowledgeObjectStatus,
    KnowledgeObjectVersion,
    Snapshot,
    Source,
    Topic,
    TopicStatus,
)
from atlas.domain.knowledge.payload import KnowledgePayloadV1
from atlas.platform.ids import (
    generate_claim_id,
    generate_evidence_id,
    generate_ko_id,
    generate_snapshot_id,
    generate_source_id,
    generate_topic_id,
)
from pydantic import HttpUrl
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_full_knowledge_object_and_traceability_lifecycle(
    db_session: AsyncSession,
) -> None:
    """End-to-end verification of Knowledge Object genesis, revisioning, and foreign-key traceability.

    Validates:
    - Invariant 1: Claim -> Evidence -> Source -> Snapshot resolution
    - Invariant 3: Structured assertions
    - Invariant 4: Append-only immutability
    - ADR-0003: Row-per-version with current pointer
    """
    source_repo = SourceRepository(db_session)
    ko_repo = KnowledgeRepository(db_session)
    now = datetime(2026, 7, 30, 10, 0, 0, tzinfo=UTC)

    # 1. Create Topic
    topic_id = generate_topic_id()
    topic = Topic(
        id=topic_id,
        title="Origins of Panthera Tigris",
        domain_id="dom_animal",
        entity_id=None,
        status=TopicStatus.APPROVED,
        created_at=now,
    )
    await source_repo.save_topic(topic)

    # 2. Create Source
    source_id = generate_source_id()
    source = Source(
        id=source_id,
        url=HttpUrl("https://nature.example.com/articles/tiger-evolution-2024"),
        title="Phylogenetic history of the tiger (Panthera tigris)",
        author="Dr. Jane Smith et al.",
        published_date=date(2024, 3, 15),
        source_tier=SourceTier.PEER_REVIEWED,
        created_at=now,
    )
    await source_repo.save_source(source)

    # 3. Create content-addressed Snapshot
    content_bytes = (
        b"<html><body>Tiger genomic sequencing reveals origins in East Asia ~2 Ma.</body></html>"
    )
    content_hash = hashlib.sha256(content_bytes).hexdigest()
    snapshot_id = generate_snapshot_id()
    snapshot = Snapshot(
        id=snapshot_id,
        source_id=source_id,
        content_hash=content_hash,
        storage_key="sha256/19/71/197121f4b25e4e120a8473734f4478f111e6fb1881949305a847134a6b02b328",
        mime_type="text/html",
        byte_size=len(content_bytes),
        retrieved_at=now,
    )
    await source_repo.save_snapshot(snapshot)

    # 4. Create Evidence
    evidence_id = generate_evidence_id()
    evidence = Evidence(
        id=evidence_id,
        source_id=source_id,
        snapshot_id=snapshot_id,
        locator="p. 14, col. 2, para 3",
        quote="Genomic analysis places the crown clade origin of Panthera tigris in East Asia at approximately 2.0 Ma.",
        stance=EvidenceStance.SUPPORTS,
        confidence=0.98,
        extracted_at=now,
    )
    await source_repo.save_evidence(evidence)

    # 5. Create Claim linked to Evidence
    claim_id = generate_claim_id()
    claim = Claim(
        id=claim_id,
        text="Tigers originated in East Asia approximately 2 million years ago.",
        assertion_type=AssertionType.FACT,
        confidence=0.98,
        status=ClaimStatus.VERIFIED,
        created_at=now,
    )
    await source_repo.save_claim(claim, actor_id="test.seed", reason="Fixture seed")
    await source_repo.link_claim_evidence(
        ClaimEvidenceLink(
            claim_id=claim_id,
            evidence_id=evidence_id,
            stance=EvidenceStance.SUPPORTS,
            notes="Direct genetic confirmation",
        )
    )

    # 6. Genesis Revision: Create Knowledge Object v1
    ko_id = generate_ko_id()
    ko_v1 = KnowledgeObjectVersion(
        ko_id=ko_id,
        version=1,
        topic_id=topic_id,
        entity_id=None,
        status=KnowledgeObjectStatus.VERIFIED,
        quality_score=85.0,
        confidence=0.95,
        actor_id="operator_agent_01",
        reason="Initial research synthesis for tiger origins topic",
        payload=KnowledgePayloadV1(
            schema_version=1,
            summary="Tigers originated in East Asia approximately 2 Ma.",
            angles=["The ancient cradle of the tiger"],
            keywords=["tiger", "evolution", "east asia"],
            psychology_notes=["Awe of prehistoric origin"],
            metadata={"primary_source_count": 1},
        ),
        claim_ids=[claim_id],
        created_at=now,
    )
    await ko_repo.save_version(ko_v1, make_current=True)

    # Verify Current Pointer points to v1
    current_v1 = await ko_repo.get_current(ko_id)
    assert current_v1 is not None
    assert current_v1.version == 1
    assert current_v1.payload.summary == "Tigers originated in East Asia approximately 2 Ma."

    # 7. Revision: Create Knowledge Object v2 (Immutability check)
    later = datetime(2026, 7, 30, 11, 0, 0, tzinfo=UTC)
    ko_v2 = KnowledgeObjectVersion(
        ko_id=ko_id,
        version=2,
        topic_id=topic_id,
        entity_id=None,
        status=KnowledgeObjectStatus.VERIFIED,
        quality_score=92.0,
        confidence=0.97,
        actor_id="operator_agent_01",
        reason="Expanded narrative angles and refined Pleistocene timeline",
        payload=KnowledgePayloadV1(
            schema_version=1,
            summary="Comprehensive evolutionary history of Panthera tigris across Pleistocene Asia.",
            angles=["The ancient cradle of the tiger", "Pleistocene dispersal corridor"],
            keywords=["tiger", "phylogenetics", "pleistocene"],
            psychology_notes=["Origin fascination", "Survival against glacial shifts"],
            metadata={"primary_source_count": 1, "operator_reviewed": True},
        ),
        claim_ids=[claim_id],
        created_at=later,
    )
    await ko_repo.save_version(ko_v2, make_current=True)

    # 8. Verify Current Pointer now points to v2
    current_v2 = await ko_repo.get_current(ko_id)
    assert current_v2 is not None
    assert current_v2.version == 2
    assert current_v2.quality_score == 92.0
    assert "Pleistocene dispersal corridor" in current_v2.payload.angles

    # 9. Verify Version 1 is intact and immutable
    read_v1 = await ko_repo.get_version(ko_id, version=1)
    assert read_v1 is not None
    assert read_v1.version == 1
    assert read_v1.quality_score == 85.0
    assert read_v1.payload.summary == "Tigers originated in East Asia approximately 2 Ma."
    assert len(read_v1.payload.angles) == 1

    # 10. Verify Full History Retrieval
    history = await ko_repo.get_history(ko_id)
    assert len(history) == 2
    assert [v.version for v in history] == [1, 2]

    # 11. Verify Traceability Chain (Claim -> Evidence -> Source -> Snapshot)
    chain = await ko_repo.get_traceability_chain(claim_id)
    assert chain.claim.id == claim_id
    assert chain.claim.text == "Tigers originated in East Asia approximately 2 million years ago."
    assert len(chain.evidence_with_sources) == 1

    link_item, ev_item, src_item, snp_item = chain.evidence_with_sources[0]
    assert link_item.claim_id == claim_id
    assert link_item.evidence_id == evidence_id
    assert ev_item.id == evidence_id
    assert ev_item.locator == "p. 14, col. 2, para 3"
    assert src_item.id == source_id
    assert str(src_item.url) == "https://nature.example.com/articles/tiger-evolution-2024"
    assert snp_item.id == snapshot_id
    assert snp_item.content_hash == content_hash


@pytest.mark.asyncio
async def test_foreign_key_constraints_enforce_traceability_integrity(
    db_session: AsyncSession,
) -> None:
    """Verify that PostgreSQL foreign key constraints strictly block corrupted traceability relations."""
    source_repo = SourceRepository(db_session)
    now = datetime(2026, 7, 30, 10, 0, 0, tzinfo=UTC)

    # 1. Attempt to create Snapshot referencing non-existent Source (MUST FAIL)
    snapshot = Snapshot(
        id=generate_snapshot_id(),
        source_id="src_non_existent_00000000000000",
        content_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        storage_key="s3://atlas/fake.html",
        mime_type="text/html",
        byte_size=0,
        retrieved_at=now,
    )
    with pytest.raises(IntegrityError):
        await source_repo.save_snapshot(snapshot)

    await db_session.rollback()

    # 2. Attempt to create Evidence referencing non-existent Source/Snapshot (MUST FAIL)
    evidence = Evidence(
        id=generate_evidence_id(),
        source_id="src_fake",
        snapshot_id="snp_fake",
        locator="p. 1",
        quote="Fake quote.",
        stance=EvidenceStance.SUPPORTS,
        confidence=1.0,
        extracted_at=now,
    )
    with pytest.raises(IntegrityError):
        await source_repo.save_evidence(evidence)

    await db_session.rollback()


@pytest.mark.asyncio
async def test_claim_usage_impact_index_for_retractions(
    db_session: AsyncSession,
) -> None:
    """Verify ClaimUsage impact index correctly maps claims to published render beats (SPEC §3)."""
    source_repo = SourceRepository(db_session)
    now = datetime(2026, 7, 30, 10, 0, 0, tzinfo=UTC)

    # Create Claim
    claim_id = generate_claim_id()
    claim = Claim(
        id=claim_id,
        text="A contested scientific assertion.",
        assertion_type=AssertionType.CONTESTED,
        confidence=0.5,
        status=ClaimStatus.CONTESTED,
        created_at=now,
    )
    await source_repo.save_claim(claim, actor_id="test.seed", reason="Fixture seed")

    # Record Claim Usage in Render Output
    usage = ClaimUsage(
        id="usg_rnd_2026_07_01",
        claim_id=claim_id,
        render_id="rnd_2026_07_origins_001",
        beat_id="beat_03_argument",
        used_at=now,
    )
    await source_repo.record_claim_usage(usage)

    # Query Impact Index for Retractions
    usages = await source_repo.get_claim_usages(claim_id)
    assert len(usages) == 1
    assert usages[0].render_id == "rnd_2026_07_origins_001"
    assert usages[0].beat_id == "beat_03_argument"
