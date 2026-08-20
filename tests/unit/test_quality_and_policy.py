"""Unit tests for Quality Rubric, License Policy, Gate Policy, and Response Cache."""

import pytest
from atlas.application.policies.gate_policy import GatePolicy, PipelineStage
from atlas.application.policies.license_policy import LicensePolicy
from atlas.domain.execution.models import GateType
from atlas.domain.quality.models import (
    RUBRIC_WEIGHTS,
    DimensionScore,
    QualityReport,
    RubricDimension,
)
from atlas.platform.cache import ResponseCache
from atlas.platform.clock import utc_now
from atlas.platform.errors import LicenseIncompatibleError, RateLimitExceededError
from atlas.platform.quota import QuotaManager


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


def test_license_policy_compatibility() -> None:
    """Verify commercial license whitelist and rejection of NC/ND terms."""
    # Permissible licenses
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


@pytest.mark.asyncio
async def test_quota_manager_rate_limiting() -> None:
    """Verify sliding-window rate limiting in QuotaManager."""
    qm = QuotaManager(
        execution_repo=None,  # type: ignore[arg-type]
        provider_limits={"gemini": {"rpm": 2, "rpd": 10, "tpm": 1000, "tpd": 10000}},
    )
    provider = "gemini"

    # Rapidly consume 2 calls (the limit)
    qm.check_rate_limits(provider)
    await qm.record_invocation(
        provider=provider,
        model_id="gemini-1.5-flash",
        prompt_version="v1",
        parameters={},
        code_version="v1",
        input_tokens=10,
        output_tokens=10,
        latency_ms=10,
    )
    qm.check_rate_limits(provider)
    await qm.record_invocation(
        provider=provider,
        model_id="gemini-1.5-flash",
        prompt_version="v1",
        parameters={},
        code_version="v1",
        input_tokens=10,
        output_tokens=10,
        latency_ms=10,
    )

    # 3rd call must raise RateLimitExceededError
    with pytest.raises(RateLimitExceededError) as exc_info:
        qm.check_rate_limits(provider)
    assert exc_info.value.provider == provider
    assert exc_info.value.limit_type == "RPM"
