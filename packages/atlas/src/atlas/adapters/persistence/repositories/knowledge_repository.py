"""Repository for Knowledge Objects, row-per-version lifecycle, and traceability."""

from atlas.adapters.persistence.tables import (
    ClaimEvidenceTable,
    ClaimTable,
    EvidenceTable,
    KnowledgeObjectClaimTable,
    KnowledgeObjectCurrentTable,
    KnowledgeObjectVersionTable,
    SnapshotTable,
    SourceTable,
)
from atlas.domain.knowledge.models import (
    AssertionType,
    Claim,
    ClaimStatus,
    Evidence,
    EvidenceStance,
    KnowledgeObjectStatus,
    KnowledgeObjectVersion,
    Snapshot,
    Source,
    SourceTier,
)
from atlas.domain.knowledge.upcast import upcast_knowledge_payload
from atlas.platform.clock import utc_now
from atlas.platform.errors import KnowledgeObjectNotFoundError
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession


class TraceabilityChain:
    """Resolved traceability tree for a Claim."""

    def __init__(
        self,
        claim: Claim,
        evidence_with_sources: list[tuple[Evidence, Source, Snapshot]],
    ) -> None:
        self.claim = claim
        self.evidence_with_sources = evidence_with_sources


class KnowledgeRepository:
    """Data access repository for Knowledge Objects and Traceability."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save_version(
        self, ko: KnowledgeObjectVersion, make_current: bool = True
    ) -> KnowledgeObjectVersion:
        """Atomically persist a Knowledge Object revision and update current pointer."""
        # 1. Insert revision row
        version_row = KnowledgeObjectVersionTable(
            ko_id=ko.ko_id,
            version=ko.version,
            topic_id=ko.topic_id,
            entity_id=ko.entity_id,
            status=ko.status.value,
            quality_score=ko.quality_score,
            confidence=ko.confidence,
            actor_id=ko.actor_id,
            reason=ko.reason,
            payload=ko.payload.model_dump(mode="json"),
            created_at=ko.created_at,
        )
        self.session.add(version_row)

        # 2. Insert claim associations
        for claim_id in ko.claim_ids:
            claim_link = KnowledgeObjectClaimTable(
                ko_id=ko.ko_id,
                version=ko.version,
                claim_id=claim_id,
            )
            self.session.add(claim_link)

        # 3. Update current pointer
        if make_current:
            await self.session.flush()
            # Remove existing current pointer if any
            await self.session.execute(
                delete(KnowledgeObjectCurrentTable).where(
                    KnowledgeObjectCurrentTable.ko_id == ko.ko_id
                )
            )
            current_row = KnowledgeObjectCurrentTable(
                ko_id=ko.ko_id,
                current_version=ko.version,
                updated_at=utc_now(),
            )
            self.session.add(current_row)

        await self.session.flush()
        return ko

    async def get_current(self, ko_id: str) -> KnowledgeObjectVersion:
        """Retrieve the current active version of a Knowledge Object."""
        stmt = (
            select(KnowledgeObjectVersionTable)
            .join(
                KnowledgeObjectCurrentTable,
                (KnowledgeObjectVersionTable.ko_id == KnowledgeObjectCurrentTable.ko_id)
                & (
                    KnowledgeObjectVersionTable.version
                    == KnowledgeObjectCurrentTable.current_version
                ),
            )
            .where(KnowledgeObjectVersionTable.ko_id == ko_id)
        )
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        if not row:
            raise KnowledgeObjectNotFoundError(ko_id)

        claim_ids = await self._get_claim_ids(row.ko_id, row.version)
        return self._to_domain(row, claim_ids)

    async def get_version(self, ko_id: str, version: int) -> KnowledgeObjectVersion:
        """Retrieve a specific historical version of a Knowledge Object."""
        stmt = select(KnowledgeObjectVersionTable).where(
            (KnowledgeObjectVersionTable.ko_id == ko_id)
            & (KnowledgeObjectVersionTable.version == version)
        )
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        if not row:
            raise KnowledgeObjectNotFoundError(ko_id, version=version)

        claim_ids = await self._get_claim_ids(row.ko_id, row.version)
        return self._to_domain(row, claim_ids)

    async def get_history(self, ko_id: str) -> list[KnowledgeObjectVersion]:
        """Retrieve all historical revisions for a Knowledge Object in chronological order."""
        stmt = (
            select(KnowledgeObjectVersionTable)
            .where(KnowledgeObjectVersionTable.ko_id == ko_id)
            .order_by(KnowledgeObjectVersionTable.version.asc())
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        if not rows:
            raise KnowledgeObjectNotFoundError(ko_id)

        history = []
        for row in rows:
            claim_ids = await self._get_claim_ids(row.ko_id, row.version)
            history.append(self._to_domain(row, claim_ids))
        return history

    async def get_traceability_chain(self, claim_id: str) -> TraceabilityChain:
        """Resolve the full Claim -> Evidence -> Source -> Snapshot provenance tree."""
        # 1. Fetch Claim
        claim_stmt = select(ClaimTable).where(ClaimTable.id == claim_id)
        claim_row = (await self.session.execute(claim_stmt)).scalar_one_or_none()
        if not claim_row:
            raise KnowledgeObjectNotFoundError(f"Claim {claim_id}")

        claim = Claim(
            id=claim_row.id,
            text=claim_row.text,
            assertion_type=AssertionType(claim_row.assertion_type),
            confidence=claim_row.confidence,
            status=ClaimStatus(claim_row.status),
            inferred_from_claim_ids=list(claim_row.inferred_from_claim_ids or []),
            created_at=claim_row.created_at,
        )

        # 2. Fetch linked Evidence, Sources, and Snapshots
        stmt = (
            select(EvidenceTable, SourceTable, SnapshotTable)
            .join(ClaimEvidenceTable, ClaimEvidenceTable.evidence_id == EvidenceTable.id)
            .join(SourceTable, EvidenceTable.source_id == SourceTable.id)
            .join(SnapshotTable, EvidenceTable.snapshot_id == SnapshotTable.id)
            .where(ClaimEvidenceTable.claim_id == claim_id)
        )
        result = await self.session.execute(stmt)

        evidence_with_sources = []
        for ev_row, src_row, snp_row in result.all():
            evidence = Evidence(
                id=ev_row.id,
                source_id=ev_row.source_id,
                snapshot_id=ev_row.snapshot_id,
                locator=ev_row.locator,
                quote=ev_row.quote,
                stance=EvidenceStance(ev_row.stance),
                confidence=ev_row.confidence,
                extracted_at=ev_row.extracted_at,
            )
            source = Source(
                id=src_row.id,
                url=src_row.url,
                title=src_row.title,
                author=src_row.author,
                published_date=src_row.published_date,
                source_tier=SourceTier(src_row.source_tier),
                created_at=src_row.created_at,
            )
            snapshot = Snapshot(
                id=snp_row.id,
                source_id=snp_row.source_id,
                content_hash=snp_row.content_hash,
                storage_key=snp_row.storage_key,
                mime_type=snp_row.mime_type,
                byte_size=snp_row.byte_size,
                retrieved_at=snp_row.retrieved_at,
            )
            evidence_with_sources.append((evidence, source, snapshot))

        return TraceabilityChain(claim=claim, evidence_with_sources=evidence_with_sources)

    async def _get_claim_ids(self, ko_id: str, version: int) -> list[str]:
        """Fetch claim IDs associated with a specific version."""
        stmt = select(KnowledgeObjectClaimTable.claim_id).where(
            (KnowledgeObjectClaimTable.ko_id == ko_id)
            & (KnowledgeObjectClaimTable.version == version)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    def _to_domain(
        self, row: KnowledgeObjectVersionTable, claim_ids: list[str]
    ) -> KnowledgeObjectVersion:
        """Convert database row to KnowledgeObjectVersion domain model with upcast."""
        payload = upcast_knowledge_payload(row.payload)
        return KnowledgeObjectVersion(
            ko_id=row.ko_id,
            version=row.version,
            topic_id=row.topic_id,
            entity_id=row.entity_id,
            status=KnowledgeObjectStatus(row.status),
            quality_score=row.quality_score,
            confidence=row.confidence,
            actor_id=row.actor_id,
            reason=row.reason,
            payload=payload,
            claim_ids=claim_ids,
            created_at=row.created_at,
        )
