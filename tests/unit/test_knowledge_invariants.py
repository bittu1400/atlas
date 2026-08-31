"""Unit tests for Knowledge Invariants as specified in SPEC §3."""

from datetime import UTC, datetime

import pytest
from atlas.domain.knowledge.invariants import validate_claim_publication_readiness
from atlas.domain.knowledge.models import (
    AssertionType,
    Claim,
    ClaimEvidenceLink,
    ClaimStatus,
    EvidenceStance,
)
from atlas.platform.errors import TraceabilityConstraintError, UnsupportedClaimError
from pydantic import ValidationError


def test_rejects_verified_claim_without_evidence() -> None:
    """Invariant 1 & 2: A Claim marked verified with 0 evidence must raise UnsupportedClaimError."""
    claim = Claim(
        id="clm_01",
        text="Tigers are the largest cat species.",
        assertion_type=AssertionType.FACT,
        confidence=1.0,
        status=ClaimStatus.VERIFIED,
        created_at=datetime.now(UTC),
    )
    with pytest.raises(UnsupportedClaimError, match="0 supporting evidence"):
        validate_claim_publication_readiness(claim, evidence_links=[])


def test_rejects_unsupported_claim_on_publication_path() -> None:
    """Invariant 2: An unsupported claim cannot be published."""
    claim = Claim(
        id="clm_02",
        text="Tigers fly at night.",
        assertion_type=AssertionType.FACT,
        confidence=0.1,
        status=ClaimStatus.UNSUPPORTED,
        created_at=datetime.now(UTC),
    )
    with pytest.raises(UnsupportedClaimError, match="cannot be published"):
        validate_claim_publication_readiness(claim, evidence_links=[])


def test_rejects_inference_claim_without_parent_claims() -> None:
    """Invariant 3: Inference claim must name the Claims it was inferred from."""
    claim = Claim(
        id="clm_03",
        text="Therefore tiger habitats are shrinking due to agriculture.",
        assertion_type=AssertionType.INFERENCE,
        confidence=0.9,
        status=ClaimStatus.VERIFIED,
        inferred_from_claim_ids=[],  # Missing parent claims!
        created_at=datetime.now(UTC),
    )
    with pytest.raises(TraceabilityConstraintError, match="inferred_from_claim_ids"):
        validate_claim_publication_readiness(
            claim,
            evidence_links=[
                ClaimEvidenceLink(
                    claim_id=claim.id, evidence_id="e", stance=EvidenceStance.SUPPORTS, notes=None
                )
                for _ in range(2)
            ],
        )


def test_allows_valid_fact_claim_with_evidence() -> None:
    """Valid fact claim with supporting evidence passes."""
    claim = Claim(
        id="clm_04",
        text="Panthera tigris is an apex predator.",
        assertion_type=AssertionType.FACT,
        confidence=1.0,
        status=ClaimStatus.VERIFIED,
        created_at=datetime.now(UTC),
    )
    # Should not raise
    validate_claim_publication_readiness(
        claim,
        evidence_links=[
            ClaimEvidenceLink(
                claim_id=claim.id, evidence_id="e", stance=EvidenceStance.SUPPORTS, notes=None
            )
            for _ in range(1)
        ],
    )


def test_allows_valid_inference_with_parent_claims_and_evidence() -> None:
    """Valid inference claim with parents and evidence passes."""
    claim = Claim(
        id="clm_05",
        text="Therefore SUBJECT_A declined across PLACEHOLDER_PERIOD_E.",
        assertion_type=AssertionType.INFERENCE,
        confidence=0.95,
        status=ClaimStatus.VERIFIED,
        inferred_from_claim_ids=["clm_01", "clm_04"],
        created_at=datetime.now(UTC),
    )
    # Should not raise
    validate_claim_publication_readiness(
        claim,
        evidence_links=[
            ClaimEvidenceLink(
                claim_id=claim.id, evidence_id="e", stance=EvidenceStance.SUPPORTS, notes=None
            )
            for _ in range(1)
        ],
    )


def test_claim_confidence_bounds() -> None:
    Claim(
        id="c1",
        text="A",
        assertion_type=AssertionType.FACT,
        confidence=0.0,
        status=ClaimStatus.UNSUPPORTED,
        created_at=datetime.now(UTC),
    )
    Claim(
        id="c2",
        text="B",
        assertion_type=AssertionType.FACT,
        confidence=1.0,
        status=ClaimStatus.UNSUPPORTED,
        created_at=datetime.now(UTC),
    )

    with pytest.raises(ValidationError):
        Claim(
            id="c3",
            text="C",
            assertion_type=AssertionType.FACT,
            confidence=-0.1,
            status=ClaimStatus.UNSUPPORTED,
            created_at=datetime.now(UTC),
        )
    with pytest.raises(ValidationError):
        Claim(
            id="c4",
            text="D",
            assertion_type=AssertionType.FACT,
            confidence=1.1,
            status=ClaimStatus.UNSUPPORTED,
            created_at=datetime.now(UTC),
        )


def test_validate_claim_publication_readiness_stance() -> None:
    claim = Claim(
        id="c1",
        text="A",
        assertion_type=AssertionType.FACT,
        confidence=0.5,
        status=ClaimStatus.VERIFIED,
        created_at=datetime.now(UTC),
    )
    supports = ClaimEvidenceLink(
        claim_id="c1", evidence_id="e1", stance=EvidenceStance.SUPPORTS, notes=None
    )
    contradicts = ClaimEvidenceLink(
        claim_id="c1", evidence_id="e2", stance=EvidenceStance.CONTRADICTS, notes=None
    )

    with pytest.raises(UnsupportedClaimError, match="0 supporting evidence items"):
        validate_claim_publication_readiness(claim, [])
    with pytest.raises(UnsupportedClaimError, match="0 supporting evidence items"):
        validate_claim_publication_readiness(claim, [contradicts])

    validate_claim_publication_readiness(claim, [supports, contradicts])
