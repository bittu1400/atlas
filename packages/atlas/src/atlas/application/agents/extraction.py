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
)
from atlas.platform.logging import get_logger
from atlas.platform.quota import QuotaManager
from atlas.prompts.loader import render_prompt

logger = get_logger("application.agents.extraction")


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
        raw_text = content_bytes.decode("utf-8", errors="replace")[:8000]

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
        self.quota_mgr.check_rate_limits(route.provider)

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
            provider=route.provider,
            model_id=route.model_id,
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

        # 6. Save extracted Evidence records
        evidence_domain_objs: list[Evidence] = []
        for ev_item in payload.evidence:
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

        # 7. Save extracted Claims and explicit links
        claim_domain_objs: list[Claim] = []
        for cl_item in payload.claims:
            cl = Claim(
                id=generate_claim_id(),
                text=cl_item.text,
                assertion_type=cl_item.assertion_type,
                confidence=cl_item.confidence,
                status=ClaimStatus.VERIFIED,  # Candidate for verification agent pass
                created_at=utc_now(),
            )
            await self.source_repo.save_claim(cl)
            claim_domain_objs.append(cl)

        # 8. Link Claims to Evidence
        for link_item in payload.links:
            if link_item.claim_index < len(claim_domain_objs) and link_item.evidence_index < len(
                evidence_domain_objs
            ):
                link = ClaimEvidenceLink(
                    claim_id=claim_domain_objs[link_item.claim_index].id,
                    evidence_id=evidence_domain_objs[link_item.evidence_index].id,
                    stance=link_item.stance,
                    notes=link_item.notes,
                )
                await self.source_repo.link_claim_evidence(link)

        # 9. Create or update Knowledge Object Version
        ko_id = f"ko_{topic_id}"
        all_claim_ids = [c.id for c in claim_domain_objs]
        ko_version = KnowledgeObjectVersion(
            ko_id=ko_id,
            version=1,
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
            ko_version=1,
        )
