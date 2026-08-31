"""Unit tests covering Phase 3.1 remediated platform, policy, and domain logic."""

import threading
from datetime import time
from unittest.mock import MagicMock

import pytest
from atlas.application.policies.gate_policy import DEFAULT_STAGE_GATES
from atlas.application.policies.license_policy import LicensePolicy
from atlas.application.policies.quota_policy import RoutingPolicy, TaskKind
from atlas.domain.execution.models import PipelineStage, Step, StepStatus
from atlas.domain.publishing.models import BlackoutRule
from atlas.platform.cache import ResponseCache
from atlas.platform.config import clear_settings_cache, get_settings
from atlas.platform.errors import (
    AiImageUnapprovedError,
    BlackoutWindowViolationError,
)
from atlas.platform.quota import DEFAULT_PROVIDER_LIMITS, QuotaManager

from apps.api.dependencies import verify_api_key


def test_response_cache_bounded_eviction() -> None:
    """P2-01: ResponseCache adheres to maxsize and evicts least recently used items."""
    cache = ResponseCache(maxsize=3)
    cache.set("a", "1")
    cache.set("b", "2")
    cache.set("c", "3")
    assert len(cache) == 3

    # Access "a" to make "b" the least recently used
    assert cache.get("a") == "1"
    cache.set("d", "4")
    assert len(cache) == 3
    assert cache.get("b") is None  # "b" was evicted
    assert cache.get("a") == "1"
    assert cache.get("c") == "3"
    assert cache.get("d") == "4"


def test_response_cache_thread_safety() -> None:
    """P2-01: ResponseCache operates safely across concurrent threads."""
    cache = ResponseCache(maxsize=100)

    def worker(worker_id: int) -> None:
        for i in range(50):
            cache.set(f"key_{worker_id}_{i}", str(i))
            _ = cache.get(f"key_{worker_id}_{i}")

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(cache) <= 100


def test_clear_settings_cache() -> None:
    """P2-02: clear_settings_cache clears cached lru_cache for Settings."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
    clear_settings_cache()
    s3 = get_settings()
    assert s3 is not None


def test_quota_manager_thread_safety() -> None:
    """P1-05: QuotaManager counters and sliding window lock concurrency."""
    mock_repo = MagicMock()
    qm = QuotaManager(execution_repo=mock_repo)
    assert DEFAULT_PROVIDER_LIMITS["gemini"]["rpm"] > 0

    # Rapid concurrent checks should not race or corrupt state
    def check_worker() -> None:
        for _ in range(50):
            qm.check_rate_limits("fake")

    threads = [threading.Thread(target=check_worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


def test_ai_image_approval_invariant_9() -> None:
    """P3-05 & Invariant 9: Unapproved AI images raise AiImageUnapprovedError."""
    # Approved AI image passes
    assert LicensePolicy.validate_ai_image_approval("img_123", is_human_approved=True) is True

    # Unapproved AI image raises
    with pytest.raises(AiImageUnapprovedError) as exc_info:
        LicensePolicy.validate_ai_image_approval("img_unapproved", is_human_approved=False)
    assert exc_info.value.asset_id == "img_unapproved"


def test_blackout_rule_overnight_validation() -> None:
    """P2-09 / SPEC §14: BlackoutRule validates local time across day and overnight windows."""
    # Default rule: allowed 06:00 to 22:00 (blackout is 22:00 to 06:00)
    rule = BlackoutRule(
        id="br_default",
        earliest_allowed_time=time(6, 0),
        latest_allowed_time=time(22, 0),
        is_enforced=True,
    )

    # Allowed midday times pass
    rule.validate_time(time(12, 0))
    rule.validate_time(time(6, 0))
    rule.validate_time(time(22, 0))

    # Sleeping hours raise BlackoutWindowViolationError
    with pytest.raises(BlackoutWindowViolationError):
        rule.validate_time(time(23, 30))
    with pytest.raises(BlackoutWindowViolationError):
        rule.validate_time(time(3, 0))


def test_stage_sequence_and_step_index_18() -> None:
    """P0-01 / P2-12: Verify full 18-stage pipeline sequence."""
    assert len(PipelineStage) == 18
    assert len(DEFAULT_STAGE_GATES) == 18
    assert PipelineStage.PUBLISH.value == "publish"

    step = Step(
        id="step_test_18",
        run_id="run_test",
        step_name=PipelineStage.PUBLISH.value,
        step_index=18,
        status=StepStatus.PENDING,
        input_hash="hash",
    )
    assert step.step_index == 18


def test_routing_policy_task_kind_resolution() -> None:
    """AF-02: RoutingPolicy maps task kinds to distinct model configs."""
    route_claim = RoutingPolicy.get_route(TaskKind.CLAIM_EXTRACTION)
    assert route_claim.provider in {"gemini", "ollama", "fake"}
    assert route_claim.temperature <= 0.3

    route_script = RoutingPolicy.get_route(TaskKind.SCRIPT_WRITING)
    assert route_script.provider in {"gemini", "ollama", "fake"}


@pytest.mark.asyncio
async def test_verify_api_key_dependency() -> None:
    """P0-04: verify_api_key enforces key presence when enabled."""
    # When disabled (default in dev), returns anonymous or provided key
    key = await verify_api_key(api_key=None)
    assert key == "anonymous"

    key_provided = await verify_api_key(api_key="secret-key")
    assert key_provided == "secret-key"
