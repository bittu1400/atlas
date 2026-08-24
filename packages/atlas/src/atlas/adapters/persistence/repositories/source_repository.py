"""Repository for Topics, Sources, Snapshots, Evidence, Claims, and Claim Usages."""

from atlas.adapters.persistence.tables import (
    ClaimEvidenceTable,
    ClaimTable,
    ClaimUsageTable,
    EvidenceTable,
    SnapshotTable,
    SourceTable,
    TopicTable,
)
from atlas.domain.common.enums import SourceTier
from atlas.domain.knowledge.models import (
    AssertionType,
    Claim,
    ClaimEvidenceLink,
    ClaimStatus,
    ClaimUsage,
    Evidence,
    EvidenceStance,
    Snapshot,
    Source,
    Topic,
    TopicStatus,
)
from atlas.platform.errors import (
    SnapshotNotFoundError,
    SourceNotFoundError,
)
from pydantic import HttpUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class SourceRepository:
    """Data access repository for Primary Sources, Evidence, Claims, and Impact Usages."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # =========================================================================
    # Topics
    # =========================================================================

    async def save_topic(self, topic: Topic) -> Topic:
        """Persist or update a Topic."""
        existing = await self.session.get(TopicTable, topic.id)
        if existing:
            existing.title = topic.title
            existing.domain_id = topic.domain_id
            existing.entity_id = topic.entity_id
            existing.status = topic.status.value
        else:
            row = TopicTable(
                id=topic.id,
                title=topic.title,
                domain_id=topic.domain_id,
                entity_id=topic.entity_id,
                status=topic.status.value,
                created_at=topic.created_at,
            )
            self.session.add(row)
        await self.session.flush()
        return topic

    async def get_topic(self, topic_id: str) -> Topic | None:
        """Fetch Topic by ID."""
        row = await self.session.get(TopicTable, topic_id)
        if not row:
            return None
        return Topic(
            id=row.id,
            title=row.title,
            domain_id=row.domain_id,
            entity_id=row.entity_id,
            status=TopicStatus(row.status),
            created_at=row.created_at,
        )

    # =========================================================================
    # Sources
    # =========================================================================

    async def save_source(self, source: Source) -> Source:
        """Persist a Source record."""
        row = SourceTable(
            id=source.id,
            url=str(source.url),
            title=source.title,
            author=source.author,
            published_date=source.published_date,
            source_tier=source.source_tier.value,
            created_at=source.created_at,
        )
        self.session.add(row)
        await self.session.flush()
        return source

    async def get_source(self, source_id: str) -> Source:
        """Fetch Source by ID."""
        row = await self.session.get(SourceTable, source_id)
        if not row:
            raise SourceNotFoundError(source_id)
        return Source(
            id=row.id,
            url=HttpUrl(row.url),
            title=row.title,
            author=row.author,
            published_date=row.published_date,
            source_tier=SourceTier(row.source_tier),
            created_at=row.created_at,
        )

    # =========================================================================
    # Snapshots (Content-Addressed)
    # =========================================================================

    async def save_snapshot(self, snapshot: Snapshot) -> Snapshot:
        """Persist a content-addressed Snapshot."""
        row = SnapshotTable(
            id=snapshot.id,
            source_id=snapshot.source_id,
            content_hash=snapshot.content_hash,
            storage_key=snapshot.storage_key,
            mime_type=snapshot.mime_type,
            byte_size=snapshot.byte_size,
            retrieved_at=snapshot.retrieved_at,
        )
        self.session.add(row)
        await self.session.flush()
        return snapshot

    async def get_snapshot(self, snapshot_id: str) -> Snapshot:
        """Fetch Snapshot by ID."""
        row = await self.session.get(SnapshotTable, snapshot_id)
        if not row:
            raise SnapshotNotFoundError(snapshot_id)
        return Snapshot(
            id=row.id,
            source_id=row.source_id,
            content_hash=row.content_hash,
            storage_key=row.storage_key,
            mime_type=row.mime_type,
            byte_size=row.byte_size,
            retrieved_at=row.retrieved_at,
        )

    async def find_snapshot_by_hash(self, source_id: str, content_hash: str) -> Snapshot | None:
        """Look up Snapshot by source ID and content SHA-256 hash."""
        stmt = select(SnapshotTable).where(
            (SnapshotTable.source_id == source_id) & (SnapshotTable.content_hash == content_hash)
        )
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        if not row:
            return None
        return Snapshot(
            id=row.id,
            source_id=row.source_id,
            content_hash=row.content_hash,
            storage_key=row.storage_key,
            mime_type=row.mime_type,
            byte_size=row.byte_size,
            retrieved_at=row.retrieved_at,
        )

    # =========================================================================
    # Evidence
    # =========================================================================

    async def save_evidence(self, evidence: Evidence) -> Evidence:
        """Persist an Evidence record."""
        row = EvidenceTable(
            id=evidence.id,
            source_id=evidence.source_id,
            snapshot_id=evidence.snapshot_id,
            locator=evidence.locator,
            quote=evidence.quote,
            stance=evidence.stance.value,
            confidence=evidence.confidence,
            extracted_at=evidence.extracted_at,
        )
        self.session.add(row)
        await self.session.flush()
        return evidence

    async def get_evidence(self, evidence_id: str) -> Evidence | None:
        """Fetch Evidence by ID."""
        row = await self.session.get(EvidenceTable, evidence_id)
        if not row:
            return None
        return Evidence(
            id=row.id,
            source_id=row.source_id,
            snapshot_id=row.snapshot_id,
            locator=row.locator,
            quote=row.quote,
            stance=EvidenceStance(row.stance),
            confidence=row.confidence,
            extracted_at=row.extracted_at,
        )

    # =========================================================================
    # Claims & Evidence Linking
    # =========================================================================

    async def save_claim(self, claim: Claim) -> Claim:
        """Persist or update a Claim."""
        existing = await self.session.get(ClaimTable, claim.id)
        if existing:
            existing.text = claim.text
            existing.assertion_type = claim.assertion_type.value
            existing.confidence = claim.confidence
            existing.status = claim.status.value
            existing.inferred_from_claim_ids = list(claim.inferred_from_claim_ids)
        else:
            row = ClaimTable(
                id=claim.id,
                text=claim.text,
                assertion_type=claim.assertion_type.value,
                confidence=claim.confidence,
                status=claim.status.value,
                inferred_from_claim_ids=list(claim.inferred_from_claim_ids),
                created_at=claim.created_at,
            )
            self.session.add(row)
        await self.session.flush()
        return claim

    async def get_claim(self, claim_id: str) -> Claim | None:
        """Fetch Claim by ID."""
        row = await self.session.get(ClaimTable, claim_id)
        if not row:
            return None
        return Claim(
            id=row.id,
            text=row.text,
            assertion_type=AssertionType(row.assertion_type),
            confidence=row.confidence,
            status=ClaimStatus(row.status),
            inferred_from_claim_ids=list(row.inferred_from_claim_ids or []),
            created_at=row.created_at,
        )

    async def link_claim_evidence(self, link: ClaimEvidenceLink) -> None:
        """Associate Evidence with a Claim."""
        row = ClaimEvidenceTable(
            claim_id=link.claim_id,
            evidence_id=link.evidence_id,
            stance=link.stance.value,
            notes=link.notes,
        )
        self.session.add(row)
        await self.session.flush()

    # =========================================================================
    # Impact Index (Claim Usages for Retraction)
    # =========================================================================

    async def record_claim_usage(self, usage: ClaimUsage) -> ClaimUsage:
        """Record usage of a Claim in a published Render Beat."""
        row = ClaimUsageTable(
            id=usage.id,
            claim_id=usage.claim_id,
            render_id=usage.render_id,
            beat_id=usage.beat_id,
            used_at=usage.used_at,
        )
        self.session.add(row)
        await self.session.flush()
        return usage

    async def get_usages_for_claim(self, claim_id: str) -> list[ClaimUsage]:
        """Query impact index to find all renders and beats using a given Claim."""
        stmt = (
            select(ClaimUsageTable)
            .where(ClaimUsageTable.claim_id == claim_id)
            .order_by(ClaimUsageTable.used_at.desc())
        )
        result = await self.session.execute(stmt)
        return [
            ClaimUsage(
                id=r.id,
                claim_id=r.claim_id,
                render_id=r.render_id,
                beat_id=r.beat_id,
                used_at=r.used_at,
            )
            for r in result.scalars().all()
        ]

    get_claim_usages = get_usages_for_claim
