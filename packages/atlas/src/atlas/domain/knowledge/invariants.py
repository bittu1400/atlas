"""Pure domain invariant validators for the Knowledge System."""

from atlas.domain.knowledge.models import (
    AssertionType,
    Claim,
    ClaimEvidenceLink,
    ClaimStatus,
    EvidenceStance,
)
from atlas.platform.errors import TraceabilityConstraintError, UnsupportedClaimError


def validate_claim_publication_readiness(
    claim: Claim, evidence_links: list[ClaimEvidenceLink]
) -> None:
    """Validate that a Claim is legally ready to be published.

    Invariants checked:
    1. Every on-screen assertion must have at least one supporting piece of evidence.
    2. A Claim without evidence cannot be verified.
    3. Inferences must reference parent claims.
    """
    supporting_evidence_count = sum(
        1 for e in evidence_links if e.stance == EvidenceStance.SUPPORTS
    )
    if supporting_evidence_count == 0:
        if claim.status == ClaimStatus.VERIFIED:
            raise UnsupportedClaimError(
                f"Claim '{claim.id}' is marked verified but has 0 supporting evidence items"
            )
        raise UnsupportedClaimError(
            f"Claim '{claim.id}' cannot be published: 0 supporting evidence items"
        )

    if claim.assertion_type == AssertionType.INFERENCE and not claim.inferred_from_claim_ids:
        raise TraceabilityConstraintError(
            f"Inference claim '{claim.id}' must specify parent inferred_from_claim_ids"
        )


def validate_knowledge_object_claims_are_traceable(
    ko_id: str, version: int, claim_ids: list[str], claim_ids_with_evidence: set[str]
) -> None:
    """Refuse a Knowledge Object version that references a claim carrying no evidence link.

    Invariant 1 is enforced at the moment of persistence, not by filtering afterwards: a silently
    dropped claim leaves the invariant test green and the Knowledge Object empty (defect SC-04).
    """
    orphans = sorted({cid for cid in claim_ids if cid not in claim_ids_with_evidence})
    if orphans:
        raise TraceabilityConstraintError(
            f"Knowledge Object '{ko_id}' version {version} references claims with 0 evidence "
            f"links, refusing to save: {orphans}"
        )
