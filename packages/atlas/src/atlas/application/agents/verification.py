"""Fact Verification Agent for cross-checking claims against source evidence quotes."""

from dataclasses import dataclass

from atlas.application.agents.models import VerificationResultItem
from atlas.application.policies.quota_policy import RoutingPolicy, TaskKind
from atlas.application.ports.llm import LlmRequest, StructuredLlm
from atlas.application.ports.repositories import SourceRepositoryPort
from atlas.domain.knowledge.models import (
    Claim,
    ClaimStatus,
    EvidenceStance,
)
from atlas.platform.errors import ClaimNotFoundError, EvidenceNotFoundError, SourceNotFoundError
from atlas.platform.logging import get_logger
from atlas.platform.quota import QuotaManager
from atlas.prompts.loader import render_prompt

logger = get_logger("application.agents.verification")


@dataclass(frozen=True)
class VerificationOutcome:
    """Outcome of verifying an individual claim against its evidence."""

    claim_id: str
    evidence_id: str
    status: ClaimStatus
    stance: EvidenceStance
    rationale: str
    confidence: float


class VerificationAgent:
    """Agent that performs multi-pass factual verification against primary source evidence."""

    def __init__(
        self,
        llm: StructuredLlm,
        source_repo: SourceRepositoryPort,
        quota_mgr: QuotaManager,
    ) -> None:
        self.llm = llm
        self.source_repo = source_repo
        self.quota_mgr = quota_mgr

    async def verify_claim(
        self,
        claim_id: str,
        evidence_id: str,
        run_id: str,
        step_id: str,
    ) -> VerificationOutcome:
        """Verify an individual claim against its cited evidence quote using LLM judge."""
        logger.info("verification.claim_start", claim_id=claim_id, evidence_id=evidence_id)

        # 1. Retrieve domain records
        claim = await self.source_repo.get_claim(claim_id)
        if not claim:
            raise ClaimNotFoundError(claim_id)

        evidence = await self.source_repo.get_evidence(evidence_id)
        if not evidence:
            raise EvidenceNotFoundError(evidence_id)

        source = await self.source_repo.get_source(evidence.source_id)
        if not source:
            raise SourceNotFoundError(evidence.source_id)

        # 2. Render versioned verification prompt
        prompt_text = render_prompt(
            "fact_verification_v1",
            claim_text=claim.text,
            evidence_quote=evidence.quote,
            source_title=source.title,
            locator=evidence.locator,
        )

        # 3. Route call and meter quota
        route = RoutingPolicy.get_route(TaskKind.VERIFICATION)
        self.quota_mgr.check_rate_limits(route.provider)

        request = LlmRequest(
            prompt=prompt_text,
            prompt_version="fact_verification_v1",
            temperature=route.temperature,
            max_tokens=route.max_tokens or 1024,
        )

        extracted = await self.llm.extract(request, VerificationResultItem)

        await self.quota_mgr.record_invocation(
            provider=extracted.provider,
            model_id=extracted.model_id,
            prompt_version="fact_verification_v1",
            parameters={"temperature": route.temperature},
            code_version="phase-5-v1",
            input_tokens=extracted.input_tokens,
            output_tokens=extracted.output_tokens,
            latency_ms=extracted.latency_ms,
            run_id=run_id,
            step_id=step_id,
        )

        result: VerificationResultItem = extracted.data

        # 4. Map verification status
        raw_status = result.status.lower()
        if "verif" in raw_status:
            status = ClaimStatus.VERIFIED
        elif "refut" in raw_status:
            status = ClaimStatus.REFUTED
        elif "contest" in raw_status:
            status = ClaimStatus.CONTESTED
        else:
            status = ClaimStatus.UNSUPPORTED

        # 5. Append a new claim version carrying the verdict (Invariant 4)
        updated_claim = Claim(
            id=claim.id,
            text=claim.text,
            assertion_type=claim.assertion_type,
            confidence=min(claim.confidence, result.confidence),
            status=status,
            inferred_from_claim_ids=list(claim.inferred_from_claim_ids),
            created_at=claim.created_at,
        )
        await self.source_repo.save_claim(
            updated_claim,
            actor_id="agent.verification",
            reason=f"Verified against evidence {evidence_id}: {result.status}",
        )

        logger.info(
            "verification.claim_completed",
            claim_id=claim.id,
            status=status.value,
            stance=result.stance.value,
        )

        return VerificationOutcome(
            claim_id=claim.id,
            evidence_id=evidence.id,
            status=status,
            stance=result.stance,
            rationale=result.rationale,
            confidence=result.confidence,
        )
