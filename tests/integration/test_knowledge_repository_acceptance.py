"""Acceptance Criteria Integration Tests for Knowledge System and Traceability.

Acceptance criterion (docs/STATUS.md & docs/SPEC.md):
A Knowledge Object can be written, revised, and read back at any prior version,
with the traceability chain enforced by foreign keys rather than by application code.
"""

import hashlib
from datetime import UTC, datetime

import pytest
from atlas.adapters.persistence.repositories.knowledge_repository import KnowledgeRepository
from atlas.adapters.persistence.repositories.source_repository import SourceRepository
from atlas.domain.knowledge.models import (
    AssertionType,
    Claim,
    ClaimEvidenceLink,
    ClaimStatus,
    Evidence,
    EvidenceStance,
    KnowledgeObjectStatus,
    KnowledgeObjectVersion,
    Snapshot,
    Source,
    SourceTier,
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
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_knowledge_object_write_revise_read_prior_version(
    db_session: AsyncSession,
) -> None:
    """Acceptance Test: Write KO v1, revise to v2, read back both versions, verify traceability."""
    source_repo = SourceRepository(db_session)
    ko_repo = KnowledgeRepository(db_session)
    now = datetime(2026, 7, 30, 10, 0, 0, tzinfo=UTC)

    # 1. Create Topic
    topic_id = generate_topic_id()
    topic = Topic(
        id=topic_id,
        title="Origins of Panthera Tigris",
        domain_id="dom_animal",
        entity_id="Q19939",
        status=TopicStatus.APPROVED,
        created_at=now,
    )
    await source_repo.save_topic(topic)

    # 2. Create Source
    source_id = generate_source_id()
    source = Source(
        id=source_id,
        url="https://nature.example.com/articles/tiger-evolution-2024",
        title="Phylogenetic history of the tiger (Panthera tigris)",
        author="Dr. Jane Smith et al.",
        published_date="2024-03-15",
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
        storage_key=f"sha256/{content_hash[:2]}/{content_hash[2:4]}/{content_hash}",
        mime_type="text/html",
        byte_size=len(content_bytes),
        retrieved_at=now,
    )
    await source_repo.save_snapshot(snapshot)

    # 4. Create Evidence linked to Source and Snapshot
    evidence_id = generate_evidence_id()
    evidence = Evidence(
        id=evidence_id,
        source_id=source_id,
        snapshot_id=snapshot_id,
        locator="p. 14, col. 2, para 3",
        quote="Tiger genomic sequencing reveals origins in East Asia ~2 Ma.",
        stance=EvidenceStance.SUPPORTS,
        confidence=0.98,
        extracted_at=now,
    )
    await source_repo.save_evidence(evidence)

    # 5. Create Claim and link Evidence
    claim_id = generate_claim_id()
    claim = Claim(
        id=claim_id,
        text="Tigers originated in East Asia approximately 2 million years ago.",
        assertion_type=AssertionType.FACT,
        confidence=0.98,
        status=ClaimStatus.VERIFIED,
        created_at=now,
    )
    await source_repo.save_claim(claim)
    await source_repo.link_evidence_to_claim(
        ClaimEvidenceLink(
            claim_id=claim_id, evidence_id=evidence_id, stance=EvidenceStance.SUPPORTS
        )
    )

    # 6. Create Knowledge Object Version 1
    ko_id = generate_ko_id()
    ko_v1 = KnowledgeObjectVersion(
        ko_id=ko_id,
        version=1,
        topic_id=topic_id,
        entity_id="Q19939",
        status=KnowledgeObjectStatus.VERIFIED,
        quality_score=85.0,
        confidence=0.98,
        actor_id="agent_research_01",
        reason="Initial synthesis from primary phylogenetic literature",
        payload=KnowledgePayloadV1(
            schema_version=1,
            summary="Tigers originated in East Asia approximately 2 Ma.",
            angles=["The ancient cradle of the tiger"],
            keywords=["tiger", "phylogenetics", "east asia"],
            psychology_notes=["Origin fascination"],
            metadata={"primary_source_count": 1},
        ),
        claim_ids=[claim_id],
        created_at=now,
    )
    await ko_repo.save_version(ko_v1, make_current=True)

    # Verify v1 is current
    current_v1 = await ko_repo.get_current(ko_id)
    assert current_v1.version == 1
    assert current_v1.payload.summary == "Tigers originated in East Asia approximately 2 Ma."
    assert current_v1.claim_ids == [claim_id]

    # 7. Create revision Version 2 with new angle and updated payload
    later = datetime(2026, 7, 30, 11, 30, 0, tzinfo=UTC)
    ko_v2 = KnowledgeObjectVersion(
        ko_id=ko_id,
        version=2,
        topic_id=topic_id,
        entity_id="Q19939",
        status=KnowledgeObjectStatus.VERIFIED,
        quality_score=92.0,
        confidence=0.99,
        actor_id="operator_human",
        reason="Refined narrative angle based on operator feedback",
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
    assert current_v2.version == 2
    assert current_v2.quality_score == 92.0
    assert "Pleistocene dispersal corridor" in current_v2.payload.angles

    # 9. Verify Version 1 is intact and immutable
    read_v1 = await ko_repo.get_version(ko_id, version=1)
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

    ev_item, src_item, snp_item = chain.evidence_with_sources[0]
    assert ev_item.id == evidence_id
    assert ev_item.locator == "p. 14, col. 2, para 3"
    assert src_item.id == source_id
    assert src_item.url == "https://nature.example.com/articles/tiger-evolution-2024"
    assert snp_item.id == snapshot_id
    assert snp_item.content_hash == content_hash


@pytest.mark.asyncio
async def test_foreign_key_constraints_enforce_traceability_integrity(
    db_session: AsyncSession,
) -> None:
    """Verify that PostgreSQL foreign key constraints strictly block corrupted traceability relations."""
    source_repo = SourceRepository(db_session)
    ko_repo = KnowledgeRepository(db_session)
    now = datetime(2026, 7, 30, 10, 0, 0, tzinfo=UTC)

    # 1. Cannot insert Evidence with non-existent source_id
    fake_evidence = Evidence(
        id=generate_evidence_id(),
        source_id="src_non_existent",
        snapshot_id="snp_non_existent",
        locator="p. 1",
        quote="fake quote",
        stance=EvidenceStance.SUPPORTS,
        confidence=1.0,
        extracted_at=now,
    )
    with pytest.raises(IntegrityError):
        await source_repo.save_evidence(fake_evidence)

    await db_session.rollback()

    # 2. Cannot link non-existent Evidence to a Claim
    valid_claim = Claim(
        id=generate_claim_id(),
        text="Valid statement.",
        assertion_type=AssertionType.FACT,
        confidence=1.0,
        status=ClaimStatus.VERIFIED,
        created_at=now,
    )
    await source_repo.save_claim(valid_claim)

    invalid_link = ClaimEvidenceLink(
        claim_id=valid_claim.id,
        evidence_id="ev_does_not_exist",
        stance=EvidenceStance.SUPPORTS,
    )
    with pytest.raises(IntegrityError):
        await source_repo.link_evidence_to_claim(invalid_link)

    await db_session.rollback()

    # 3. Cannot link non-existent Claim to KnowledgeObject
    topic = Topic(
        id=generate_topic_id(),
        title="Test Topic",
        domain_id="dom_animal",
        status=TopicStatus.APPROVED,
        created_at=now,
    )
    await source_repo.save_topic(topic)

    ko_invalid_claim = KnowledgeObjectVersion(
        ko_id=generate_ko_id(),
        version=1,
        topic_id=topic.id,
        status=KnowledgeObjectStatus.DRAFT,
        confidence=1.0,
        actor_id="tester",
        reason="test",
        payload=KnowledgePayloadV1(schema_version=1, summary="test"),
        claim_ids=["clm_does_not_exist"],
        created_at=now,
    )
    with pytest.raises(IntegrityError):
        await ko_repo.save_version(ko_invalid_claim)

    await db_session.rollback()
