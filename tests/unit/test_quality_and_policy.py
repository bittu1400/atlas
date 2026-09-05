"""Unit tests for Quality Rubric, License Policy, Gate Policy, and Response Cache."""

import pytest
from atlas.application.policies.gate_policy import GatePolicy
from atlas.application.policies.license_policy import LicensePolicy, canonicalize_license
from atlas.domain.execution.models import GateType, PipelineStage
from atlas.domain.quality.models import (
    RUBRIC_WEIGHTS,
    DimensionScore,
    QualityReport,
    RubricDimension,
)
from atlas.platform.cache import ResponseCache
from atlas.platform.clock import utc_now
from atlas.platform.errors import LicenseIncompatibleError


def test_quality_rubric_dimension_weights() -> None:
    """Verify rubric dimension weights sum to exactly 100.0%."""
    total_weight = sum(RUBRIC_WEIGHTS.values())
    assert abs(total_weight - 100.0) < 1e-6


def test_quality_report_passing_gate() -> None:
    """Verify QualityReport passes when overall >= 78, floors >= 60, and checks pass."""
    now = utc_now()
    scores = [
        DimensionScore(
            dimension=dim,
            score=85.0,
            weight=RUBRIC_WEIGHTS[dim],
            reason="High quality factual execution",
        )
        for dim in RubricDimension
    ]
    deterministic_checks = {
        "sourcing_integrity": True,
        "duration_bounds": True,
        "loudness_bounds": True,
        "captions_valid": True,
    }
    report = QualityReport.evaluate(
        report_id="qr_123",
        run_id="run_123",
        scores=scores,
        deterministic_checks=deterministic_checks,
        created_at=now,
    )
    assert report.passed is True
    assert report.weighted_score >= 78.0


def test_quality_report_failing_due_to_dimension_floor() -> None:
    """Verify QualityReport fails if any dimension falls below 60.0 floor."""
    now = utc_now()
    scores = []
    for dim in RubricDimension:
        score = 55.0 if dim == RubricDimension.NOVELTY else 95.0
        scores.append(
            DimensionScore(
                dimension=dim,
                score=score,
                weight=RUBRIC_WEIGHTS[dim],
                reason="Evaluated dimension",
            )
        )
    deterministic_checks = {
        "sourcing_integrity": True,
        "duration_bounds": True,
        "loudness_bounds": True,
        "captions_valid": True,
    }
    report = QualityReport.evaluate(
        report_id="qr_123",
        run_id="run_123",
        scores=scores,
        deterministic_checks=deterministic_checks,
        created_at=now,
    )
    assert report.passed is False
    assert report.weighted_score >= 78.0  # Overall is high, but floor failed


def test_license_policy_allowlist_and_restrictions() -> None:
    """Verify license policy correctly enforces allowed vs forbidden licenses."""
    # Permitted licenses
    assert LicensePolicy.validate_asset_license("ast_01", "cc-by-4.0") is True
    assert LicensePolicy.validate_asset_license("ast_02", "cc0") is True
    assert LicensePolicy.validate_asset_license("ast_03", "public domain") is True
    assert LicensePolicy.validate_asset_license("ast_04", "pd") is True

    # Incompatible / non-commercial licenses
    with pytest.raises(LicenseIncompatibleError):
        LicensePolicy.validate_asset_license("ast_05", "cc-by-nc-4.0")

    with pytest.raises(LicenseIncompatibleError):
        LicensePolicy.validate_asset_license("ast_06", "cc-by-nd-4.0")

    with pytest.raises(LicenseIncompatibleError):
        LicensePolicy.validate_asset_license("ast_07", "all-rights-reserved")


def test_gate_policy_ai_image_mandatory_approval() -> None:
    """Verify Invariant 9: AI-generated imagery mandates human approval gate."""
    # Standard archival image
    should_susp, gate_type = GatePolicy.should_suspend(
        PipelineStage.ASSET_SELECTION, has_ai_generated_assets=False
    )
    assert should_susp is True
    assert gate_type == GateType.MANUAL

    # AI imagery mandatory approval check
    should_susp_ai, gate_type_ai = GatePolicy.should_suspend(
        PipelineStage.ASSET_SELECTION, has_ai_generated_assets=True
    )
    assert should_susp_ai is True
    assert gate_type_ai == GateType.MANUAL


def test_gate_policy_hybrid_and_contested_claims() -> None:
    """Verify SPEC §6: FACT_VERIFICATION (manual on contested) and STORY_ANGLE (hybrid)."""
    # FACT_VERIFICATION without contested claims -> does not suspend
    should_susp, gate_type = GatePolicy.should_suspend(
        PipelineStage.FACT_VERIFICATION, has_contested_claims=False
    )
    assert should_susp is False
    assert gate_type == GateType.HYBRID

    # FACT_VERIFICATION with contested claims -> suspends for operator review
    should_susp_c, gate_type_c = GatePolicy.should_suspend(
        PipelineStage.FACT_VERIFICATION, has_contested_claims=True
    )
    assert should_susp_c is True
    assert gate_type_c == GateType.HYBRID

    # STORY_ANGLE -> Atlas proposes, operator picks (always suspends as HYBRID)
    should_susp_a, gate_type_a = GatePolicy.should_suspend(PipelineStage.STORY_ANGLE)
    assert should_susp_a is True
    assert gate_type_a == GateType.HYBRID


def test_response_cache_key_determinism() -> None:
    """Verify deterministic SHA-256 response cache keys."""
    key1 = ResponseCache.compute_cache_key(
        prompt="Explain quantum physics",
        prompt_version="v1.2",
        model_id="gemini-1.5-flash",
        parameters={"temperature": 0.2, "max_tokens": 100},
    )
    key2 = ResponseCache.compute_cache_key(
        prompt="Explain quantum physics",
        prompt_version="v1.2",
        model_id="gemini-1.5-flash",
        parameters={"max_tokens": 100, "temperature": 0.2},  # Reordered dict
    )
    assert key1 == key2
    assert len(key1) == 64


# =============================================================================
# Invariant 10, defect V-10: license identifiers arrive in three dialects.
# =============================================================================


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("CC BY-SA 4.0", "cc-by-sa-4.0"),
        ("cc-by-sa-4.0", "cc-by-sa-4.0"),
        ("https://creativecommons.org/licenses/by-sa/4.0/", "cc-by-sa-4.0"),
        ("http://creativecommons.org/licenses/by-nc-nd/3.0/", "cc-by-nc-nd-3.0"),
        ("https://creativecommons.org/publicdomain/zero/1.0/", "cc0"),
        ("https://creativecommons.org/publicdomain/mark/1.0/", "pd-mark"),
        ("Public domain", "public-domain"),
    ],
)
def test_license_identifiers_canonicalize_across_adapter_dialects(raw: str, expected: str) -> None:
    """Wikimedia reports short names, the Internet Archive reports URLs."""
    assert canonicalize_license(raw) == expected


@pytest.mark.parametrize(
    "license_id",
    [
        "CC BY-SA 4.0",
        "https://creativecommons.org/licenses/by-sa/4.0/",
        "https://creativecommons.org/publicdomain/zero/1.0/",
        "Public domain",
        "cc0",
    ],
)
def test_permitted_licenses_pass_in_every_dialect(license_id: str) -> None:
    """A validly licensed asset was being discarded because of its spelling."""
    assert LicensePolicy.validate_asset_license("ast_probe", license_id) is True


@pytest.mark.parametrize(
    "license_id",
    [
        "CC BY-NC 4.0",
        "http://creativecommons.org/licenses/by-nc-nd/3.0/",
        "cc-by-nd-4.0",
        "Noncommercial use only",
        "Unknown",
        "",
    ],
)
def test_restricted_and_unresolvable_licenses_are_still_rejected(license_id: str) -> None:
    """Invariant 10 must not be weakened by the canonicalization: silence is not permission."""
    with pytest.raises(LicenseIncompatibleError):
        LicensePolicy.validate_asset_license("ast_probe", license_id)


def test_the_word_licence_is_not_read_as_noncommercial() -> None:
    """The blocked-term test used to be a substring match, and "licence" contains "nc"."""
    assert canonicalize_license("CC BY 4.0 licence").split("-")[:3] == ["cc", "by", "4.0"]
    assert LicensePolicy.validate_asset_license("ast_probe", "CC-BY-4.0") is True
