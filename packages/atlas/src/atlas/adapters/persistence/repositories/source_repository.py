"""Repository for Topics, Sources, Snapshots, Evidence, Claims, and Claim Usages."""

from atlas.adapters.persistence.tables import (
    ClaimEvidenceTable,
    ClaimTable,
    ClaimUsageTable,
    ClaimVersionTable,
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
from atlas.platform.clock import utc_now
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

    async def save_claim(self, claim: Claim, actor_id: str, reason: str) -> Claim:
        """Append a new immutable version of a Claim and return it with its version number.

        Nothing is updated in place (Invariant 4): the identity row is written once
        and every later change is a new `claim_versions` row carrying the actor and
        the reason, so a status transition is always attributable.
        """
        identity = await self.session.get(ClaimTable, claim.id)
        if identity is None:
            self.session.add(ClaimTable(id=claim.id, created_at=claim.created_at))
            await self.session.flush()

        latest = await self._latest_claim_version(claim.id)
        next_version = (latest.version + 1) if latest else 1

        self.session.add(
            ClaimVersionTable(
                claim_id=claim.id,
                version=next_version,
                text=claim.text,
                assertion_type=claim.assertion_type.value,
                confidence=claim.confidence,
                status=claim.status.value,
                inferred_from_claim_ids=list(claim.inferred_from_claim_ids),
                actor_id=actor_id,
                reason=reason,
                created_at=utc_now(),
            )
        )
        await self.session.flush()
        return claim.model_copy(update={"version": next_version})

    async def _latest_claim_version(self, claim_id: str) -> ClaimVersionTable | None:
        """Return the highest-numbered version row for a Claim, or None."""
        stmt = (
            select(ClaimVersionTable)
            .where(ClaimVersionTable.claim_id == claim_id)
            .order_by(ClaimVersionTable.version.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def get_claim(self, claim_id: str) -> Claim | None:
        """Fetch the current state of a Claim: its highest-numbered version."""
        identity = await self.session.get(ClaimTable, claim_id)
        if not identity:
            return None
        version_row = await self._latest_claim_version(claim_id)
        if not version_row:
            return None
        return Claim(
            id=identity.id,
            version=version_row.version,
            text=version_row.text,
            assertion_type=AssertionType(version_row.assertion_type),
            confidence=version_row.confidence,
            status=ClaimStatus(version_row.status),
            inferred_from_claim_ids=list(version_row.inferred_from_claim_ids or []),
            created_at=identity.created_at,
        )

    async def get_claim_history(self, claim_id: str) -> list[Claim]:
        """Return every version of a Claim, oldest first, for provenance inspection."""
        identity = await self.session.get(ClaimTable, claim_id)
        if not identity:
            return []
        stmt = (
            select(ClaimVersionTable)
            .where(ClaimVersionTable.claim_id == claim_id)
            .order_by(ClaimVersionTable.version.asc())
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return [
            Claim(
                id=identity.id,
                version=r.version,
                text=r.text,
                assertion_type=AssertionType(r.assertion_type),
                confidence=r.confidence,
                status=ClaimStatus(r.status),
                inferred_from_claim_ids=list(r.inferred_from_claim_ids or []),
                created_at=identity.created_at,
            )
            for r in rows
        ]

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
