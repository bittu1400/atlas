"""Repository for Knowledge Objects, row-per-version lifecycle, and traceability."""

from atlas.adapters.persistence.tables import (
    ClaimEvidenceTable,
    ClaimTable,
    ClaimVersionTable,
    EvidenceTable,
    KnowledgeObjectClaimTable,
    KnowledgeObjectCurrentTable,
    KnowledgeObjectVersionTable,
    SnapshotTable,
    SourceTable,
)
from atlas.domain.common.enums import SourceTier
from atlas.domain.knowledge.invariants import (
    validate_knowledge_object_claims_are_traceable,
)
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
    TraceabilityChain,
)
from atlas.domain.knowledge.upcast import upcast_knowledge_payload
from atlas.platform.clock import utc_now
from atlas.platform.errors import KnowledgeObjectNotFoundError
from pydantic import HttpUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class KnowledgeRepository:
    """Data access repository for Knowledge Objects and Traceability."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save_version(
        self, version: KnowledgeObjectVersion, make_current: bool = True
    ) -> KnowledgeObjectVersion:
        """Persist a new immutable Knowledge Object version and optionally advance the current pointer.

        Raises:
            TraceabilityConstraintError: if any referenced claim has no `claim_evidence` row.
                Invariant 1 refuses the save rather than dropping the claim (defect SC-04).
        """
        # 1. Refuse the whole version if any claim lacks evidence, before anything is written
        claim_ids_with_evidence: set[str] = set()
        if version.claim_ids:
            ev_stmt = select(ClaimEvidenceTable.claim_id).where(
                ClaimEvidenceTable.claim_id.in_(version.claim_ids)
            )
            claim_ids_with_evidence = set((await self.session.execute(ev_stmt)).scalars().all())
        validate_knowledge_object_claims_are_traceable(
            ko_id=version.ko_id,
            version=version.version,
            claim_ids=version.claim_ids,
            claim_ids_with_evidence=claim_ids_with_evidence,
        )

        # 2. Insert version row
        version_row = KnowledgeObjectVersionTable(
            ko_id=version.ko_id,
            version=version.version,
            topic_id=version.topic_id,
            entity_id=version.entity_id,
            status=version.status.value,
            quality_score=version.quality_score,
            confidence=version.confidence,
            actor_id=version.actor_id,
            reason=version.reason,
            payload=version.payload.model_dump(mode="json"),
            created_at=version.created_at,
        )
        self.session.add(version_row)

        # 3. Link every claim: the traceability check above already refused the untraceable ones
        for claim_id in version.claim_ids:
            self.session.add(
                KnowledgeObjectClaimTable(
                    ko_id=version.ko_id,
                    version=version.version,
                    claim_id=claim_id,
                )
            )

        # Flush version row to satisfy FK for current pointer
        await self.session.flush()

        # 4. Advance current pointer if requested
        if make_current:
            existing_ptr = await self.session.get(
                KnowledgeObjectCurrentTable, version.ko_id, with_for_update=True
            )
            if existing_ptr:
                if version.version != existing_ptr.current_version + 1:
                    raise ValueError(
                        f"Version must be exactly {existing_ptr.current_version + 1}, got {version.version}"
                    )
                existing_ptr.current_version = version.version
                existing_ptr.updated_at = utc_now()
            else:
                if version.version != 1:
                    raise ValueError(f"Initial version must be 1, got {version.version}")
                ptr_row = KnowledgeObjectCurrentTable(
                    ko_id=version.ko_id,
                    current_version=version.version,
                    updated_at=utc_now(),
                )
                self.session.add(ptr_row)
            await self.session.flush()

        return version

    async def get_version(self, ko_id: str, version: int) -> KnowledgeObjectVersion | None:
        """Fetch a specific version of a Knowledge Object with upcast payload."""
        stmt = select(KnowledgeObjectVersionTable).where(
            (KnowledgeObjectVersionTable.ko_id == ko_id)
            & (KnowledgeObjectVersionTable.version == version)
        )
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        if not row:
            return None

        claim_ids = await self._get_claim_ids(ko_id, version)
        return self._to_domain(row, claim_ids)

    async def get_current(self, ko_id: str) -> KnowledgeObjectVersion | None:
        """Fetch the current active version of a Knowledge Object."""
        stmt = (
            select(KnowledgeObjectVersionTable)
            .join(
                KnowledgeObjectCurrentTable,
                (KnowledgeObjectCurrentTable.ko_id == KnowledgeObjectVersionTable.ko_id)
                & (
                    KnowledgeObjectCurrentTable.current_version
                    == KnowledgeObjectVersionTable.version
                ),
            )
            .where(KnowledgeObjectVersionTable.ko_id == ko_id)
        )
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        if not row:
            return None

        claim_ids = await self._get_claim_ids(ko_id, row.version)
        return self._to_domain(row, claim_ids)

    async def get_current_for_topic(self, topic_id: str) -> KnowledgeObjectVersion | None:
        """Fetch the current Knowledge Object version for a given Topic."""
        stmt = (
            select(KnowledgeObjectVersionTable)
            .join(
                KnowledgeObjectCurrentTable,
                (KnowledgeObjectCurrentTable.ko_id == KnowledgeObjectVersionTable.ko_id)
                & (
                    KnowledgeObjectCurrentTable.current_version
                    == KnowledgeObjectVersionTable.version
                ),
            )
            .where(KnowledgeObjectVersionTable.topic_id == topic_id)
        )
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        if not row:
            return None

        claim_ids = await self._get_claim_ids(row.ko_id, row.version)
        return self._to_domain(row, claim_ids)

    async def get_history(self, ko_id: str) -> list[KnowledgeObjectVersion]:
        """Fetch the full append-only revision history of a Knowledge Object."""
        stmt = (
            select(KnowledgeObjectVersionTable)
            .where(KnowledgeObjectVersionTable.ko_id == ko_id)
            .order_by(KnowledgeObjectVersionTable.version.asc())
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        if not rows:
            return []

        # Batch-fetch all associated claim IDs in a single query (eliminates N+1)
        claims_stmt = select(
            KnowledgeObjectClaimTable.version, KnowledgeObjectClaimTable.claim_id
        ).where(KnowledgeObjectClaimTable.ko_id == ko_id)
        claim_rows = (await self.session.execute(claims_stmt)).all()

        claims_by_version: dict[int, list[str]] = {}
        for ver, cid in claim_rows:
            claims_by_version.setdefault(ver, []).append(cid)

        return [self._to_domain(row, claims_by_version.get(row.version, [])) for row in rows]

    async def get_traceability_chain(self, claim_id: str) -> TraceabilityChain:
        """Resolve the full Claim -> Evidence -> Source -> Snapshot provenance tree."""
        # 1. Fetch Claim identity and its current (highest) version
        claim_stmt = select(ClaimTable).where(ClaimTable.id == claim_id)
        claim_row = (await self.session.execute(claim_stmt)).scalar_one_or_none()
        if not claim_row:
            raise KnowledgeObjectNotFoundError(f"Claim {claim_id}")

        version_stmt = (
            select(ClaimVersionTable)
            .where(ClaimVersionTable.claim_id == claim_id)
            .order_by(ClaimVersionTable.version.desc())
            .limit(1)
        )
        version_row = (await self.session.execute(version_stmt)).scalars().first()
        if not version_row:
            raise KnowledgeObjectNotFoundError(f"Claim {claim_id} has no version rows")

        claim = Claim(
            id=claim_row.id,
            version=version_row.version,
            text=version_row.text,
            assertion_type=AssertionType(version_row.assertion_type),
            confidence=version_row.confidence,
            status=ClaimStatus(version_row.status),
            inferred_from_claim_ids=list(version_row.inferred_from_claim_ids or []),
            created_at=claim_row.created_at,
        )

        # 2. Fetch linked ClaimEvidenceLink, Evidence, Sources, and Snapshots
        stmt = (
            select(ClaimEvidenceTable, EvidenceTable, SourceTable, SnapshotTable)
            .join(EvidenceTable, ClaimEvidenceTable.evidence_id == EvidenceTable.id)
            .join(SourceTable, EvidenceTable.source_id == SourceTable.id)
            .join(SnapshotTable, EvidenceTable.snapshot_id == SnapshotTable.id)
            .where(ClaimEvidenceTable.claim_id == claim_id)
        )
        result = await self.session.execute(stmt)

        evidence_with_sources: list[tuple[ClaimEvidenceLink, Evidence, Source, Snapshot]] = []
        for link_row, ev_row, src_row, snp_row in result.all():
            link = ClaimEvidenceLink(
                claim_id=link_row.claim_id,
                evidence_id=link_row.evidence_id,
                stance=EvidenceStance(link_row.stance),
                notes=link_row.notes,
            )
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
                url=HttpUrl(src_row.url),
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
            evidence_with_sources.append((link, evidence, source, snapshot))

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
