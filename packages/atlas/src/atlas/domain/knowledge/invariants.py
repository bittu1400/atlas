"""Pure domain invariant validators for the Knowledge System."""

from atlas.domain.knowledge.models import AssertionType, Claim, ClaimStatus
from atlas.platform.errors import TraceabilityConstraintError, UnsupportedClaimError


def validate_claim_publication_readiness(claim: Claim, supporting_evidence_count: int) -> None:
    """Validate that a Claim is legally ready to be published.

    Invariants checked:
    1. Every on-screen assertion must have at least one supporting piece of evidence.
    2. A Claim without evidence cannot be verified.
    3. Inferences must reference parent claims.
    """
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
