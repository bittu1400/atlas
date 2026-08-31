"""Extraction Agent for parsing structured claims and primary evidence from source snapshots."""

from dataclasses import dataclass

from atlas.application.agents.models import ExtractionPayload
from atlas.application.policies.quota_policy import RoutingPolicy, TaskKind
from atlas.application.ports.llm import LlmRequest, StructuredLlm
from atlas.application.ports.repositories import (
    KnowledgeRepositoryPort,
    SourceRepositoryPort,
)
from atlas.application.ports.storage import Storage
from atlas.domain.knowledge.models import (
    Claim,
    ClaimEvidenceLink,
    ClaimStatus,
    Evidence,
    KnowledgeObjectStatus,
    KnowledgeObjectVersion,
    Snapshot,
    Source,
)
from atlas.domain.knowledge.payload import KnowledgePayloadV1
from atlas.platform.clock import utc_now
from atlas.platform.ids import (
    generate_claim_id,
    generate_evidence_id,
    knowledge_object_id_for_topic,
)
from atlas.platform.logging import get_logger
from atlas.platform.quota import QuotaManager
from atlas.prompts.loader import render_prompt

logger = get_logger("application.agents.extraction")


def _normalize_whitespace(text: str) -> str:
    """Normalize internal whitespace for verbatim quote comparison."""
    return " ".join(text.split())


@dataclass(frozen=True)
class ExtractionResult:
    """Outcome of claim and evidence extraction from snapshot."""

    topic_id: str
    snapshot_id: str
    claims_count: int
    evidence_count: int
    knowledge_object_id: str
    ko_version: int


class ExtractionAgent:
    """Agent that extracts structured claims and verbatim evidence from source snapshots."""

    def __init__(
        self,
        llm: StructuredLlm,
        storage: Storage,
        source_repo: SourceRepositoryPort,
        knowledge_repo: KnowledgeRepositoryPort,
        quota_mgr: QuotaManager,
    ) -> None:
        self.llm = llm
        self.storage = storage
        self.source_repo = source_repo
        self.knowledge_repo = knowledge_repo
        self.quota_mgr = quota_mgr

    async def execute(
        self,
        topic_id: str,
        topic_title: str,
        snapshot_id: str,
        run_id: str,
        step_id: str,
    ) -> ExtractionResult:
        """Extract atomic claims and cited evidence from snapshot bytes using Tier 2 LLM."""
        logger.info("extraction.start", topic_id=topic_id, snapshot_id=snapshot_id)

        # 1. Retrieve snapshot metadata and content
        snapshot: Snapshot = await self.source_repo.get_snapshot(snapshot_id)
        source: Source = await self.source_repo.get_source(snapshot.source_id)
        content_bytes = await self.storage.get(snapshot.storage_key)
        decoded_text = content_bytes.decode("utf-8", errors="replace")
        raw_text = decoded_text[:8000]

        # 2. Render versioned prompt template
        prompt_text = render_prompt(
            "claim_extraction_v1",
            topic_title=topic_title,
            source_title=source.title,
            source_url=str(source.url),
            source_tier=source.source_tier.value,
            source_text=raw_text,
        )

        # 3. Route call and verify rate limits
        route = RoutingPolicy.get_route(TaskKind.CLAIM_EXTRACTION)
        await self.quota_mgr.check_rate_limits(route.provider)

        request = LlmRequest(
            prompt=prompt_text,
            prompt_version="claim_extraction_v1",
            temperature=route.temperature,
            max_tokens=route.max_tokens or 2048,
        )

        # 4. Invoke LLM structured extraction
        extracted = await self.llm.extract(request, ExtractionPayload)

        # 5. Record quota usage in ledger
        await self.quota_mgr.record_invocation(
            provider=extracted.provider,
            model_id=extracted.model_id,
            prompt_version="claim_extraction_v1",
            parameters={"temperature": route.temperature},
            code_version="phase-5-v1",
            input_tokens=extracted.input_tokens,
            output_tokens=extracted.output_tokens,
            latency_ms=extracted.latency_ms,
            run_id=run_id,
            step_id=step_id,
        )

        payload: ExtractionPayload = extracted.data

        # 6. Save extracted Evidence records (Enforce Invariant 1: Verbatim Substring matching)
        normalized_snapshot = _normalize_whitespace(decoded_text)
        evidence_domain_objs: list[Evidence] = []
        evidence_index_map: dict[int, Evidence] = {}
        for idx, ev_item in enumerate(payload.evidence):
            normalized_quote = _normalize_whitespace(ev_item.quote)
            if normalized_quote and normalized_quote in normalized_snapshot:
                ev = Evidence(
                    id=generate_evidence_id(),
                    source_id=source.id,
                    snapshot_id=snapshot.id,
                    locator=ev_item.locator,
                    quote=ev_item.quote,
                    stance=ev_item.stance,
                    confidence=ev_item.confidence,
                    extracted_at=utc_now(),
                )
                await self.source_repo.save_evidence(ev)
                evidence_domain_objs.append(ev)
                evidence_index_map[idx] = ev
            else:
                logger.warning(
                    "evidence.rejected_not_verbatim",
                    quote=ev_item.quote,
                    snapshot_id=snapshot.id,
                )

        # 7. Save extracted Claims and explicit links
        claim_domain_objs: list[Claim] = []
        for cl_item in payload.claims:
            cl = Claim(
                id=generate_claim_id(),
                text=cl_item.text,
                assertion_type=cl_item.assertion_type,
                confidence=cl_item.confidence,
                status=ClaimStatus.UNVERIFIED,  # Unverified until VerificationAgent verifies
                created_at=utc_now(),
            )
            await self.source_repo.save_claim(
                cl,
                actor_id="agent.extraction",
                reason=f"Extracted from snapshot {snapshot.id}",
            )
            claim_domain_objs.append(cl)

        # 8. Link Claims to Evidence
        linked_claim_ids: set[str] = set()
        for link_item in payload.links:
            if (
                link_item.claim_index < len(claim_domain_objs)
                and link_item.evidence_index in evidence_index_map
            ):
                claim_id = claim_domain_objs[link_item.claim_index].id
                link = ClaimEvidenceLink(
                    claim_id=claim_id,
                    evidence_id=evidence_index_map[link_item.evidence_index].id,
                    stance=link_item.stance,
                    notes=link_item.notes,
                )
                await self.source_repo.link_claim_evidence(link)
                # Only a link that was actually written counts. Deriving this set
                # from the raw payload instead would admit claims whose only quote
                # was rejected as non-verbatim, and Invariant 1 forbids that.
                linked_claim_ids.add(claim_id)

        # 9. Create or update Knowledge Object Version
        ko_id = knowledge_object_id_for_topic(topic_id)

        all_claim_ids = []
        for c in claim_domain_objs:
            if c.id in linked_claim_ids:
                all_claim_ids.append(c.id)
            else:
                # Rule R2/Invariant 1: claim with no evidence ends unsupported
                c_unsupported = Claim(
                    id=c.id,
                    text=c.text,
                    assertion_type=c.assertion_type,
                    confidence=c.confidence,
                    status=ClaimStatus.UNSUPPORTED,
                    created_at=c.created_at,
                )
                await self.source_repo.save_claim(
                    c_unsupported,
                    actor_id="agent.extraction",
                    reason="No verbatim evidence quote survived extraction",
                )

        current_ko = await self.knowledge_repo.get_current(ko_id)
        next_version = (current_ko.version + 1) if current_ko else 1

        ko_version = KnowledgeObjectVersion(
            ko_id=ko_id,
            version=next_version,
            topic_id=topic_id,
            status=KnowledgeObjectStatus.DRAFT,
            actor_id="agent.extraction",
            reason="Automated primary source claim extraction",
            claim_ids=all_claim_ids,
            payload=KnowledgePayloadV1(
                summary=f"Automated knowledge extraction for {topic_title}.",
                angles=[f"Origin and history of {topic_title}"],
                keywords=[topic_title.lower()],
            ),
            created_at=utc_now(),
        )
        await self.knowledge_repo.save_version(ko_version)

        logger.info(
            "extraction.completed",
            claims=len(claim_domain_objs),
            evidence=len(evidence_domain_objs),
            ko_id=ko_id,
        )

        return ExtractionResult(
            topic_id=topic_id,
            snapshot_id=snapshot.id,
            claims_count=len(claim_domain_objs),
            evidence_count=len(evidence_domain_objs),
            knowledge_object_id=ko_id,
            ko_version=next_version,
        )
