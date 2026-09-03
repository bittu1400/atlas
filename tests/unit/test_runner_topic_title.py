"""Unit tests verifying PipelineRunner loads and passes real Topic.title (T-22)."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from atlas.application.pipeline.runner import PipelineRunner
from atlas.domain.execution.models import (
    PipelineStage,
    Run,
    RunStatus,
    Step,
    StepStatus,
)
from atlas.domain.focus.models import (
    Facet,
    FocusSnapshot,
    ScopeMode,
)
from atlas.domain.knowledge.models import Topic, TopicStatus
from atlas.platform.clock import utc_now


@pytest.fixture
def mock_runner() -> Any:
    """Create a PipelineRunner with mocked dependencies for testing title resolution."""
    runner = object.__new__(PipelineRunner)
    runner.source_repo = AsyncMock()
    runner.knowledge_repo = AsyncMock()
    runner.execution_repo = AsyncMock()
    runner.production_repo = AsyncMock()
    runner.research_agent = AsyncMock()
    runner.extraction_agent = AsyncMock()
    runner.script_agent = AsyncMock()
    runner.judge_agent = AsyncMock()
    runner.image_search = AsyncMock()
    runner.storyboard_agent = AsyncMock()
    runner.renderer = AsyncMock()
    runner.notifier = AsyncMock()
    runner.quota_mgr = AsyncMock()
    runner.publisher = AsyncMock()
    return runner


@pytest.mark.asyncio
async def test_resolve_topic_title_returns_real_title(mock_runner: Any) -> None:
    """Verify _resolve_topic_title returns the human-readable title when topic exists."""
    real_topic = Topic(
        id="topic_geometry",
        title="Origins of Euclidean Geometry",
        domain_id="dom_math",
        status=TopicStatus.PROPOSED,
        created_at=utc_now(),
    )
    mock_runner.source_repo.get_topic.return_value = real_topic

    resolved = await mock_runner._resolve_topic_title("topic_geometry")
    assert resolved == "Origins of Euclidean Geometry"
    mock_runner.source_repo.get_topic.assert_awaited_once_with("topic_geometry")


@pytest.mark.asyncio
async def test_resolve_topic_title_falls_back_to_id(mock_runner: Any) -> None:
    """Verify _resolve_topic_title falls back to topic_id when topic row is missing."""
    mock_runner.source_repo.get_topic.return_value = None

    resolved = await mock_runner._resolve_topic_title("unknown_topic")
    assert resolved == "unknown_topic"


@pytest.mark.asyncio
async def test_stages_receive_real_topic_title(mock_runner: Any) -> None:
    """Verify Research, Extraction, Script, and Quality stages pass real topic title (T-22)."""
    now = utc_now()
    real_topic = Topic(
        id="origin_of_mathematics",
        title="History of Ancient Mathematics",
        domain_id="dom_math",
        status=TopicStatus.PROPOSED,
        created_at=now,
    )
    mock_runner.source_repo.get_topic.return_value = real_topic

    run = Run(
        id="run_test_01",
        topic_id="origin_of_mathematics",
        channel_id="origins",
        status=RunStatus.RUNNING,
        captured_focus=FocusSnapshot(
            focus_id="focus_01",
            scope_mode=ScopeMode.SOFT,
            facets=[Facet(dimension="domain", value="Mathematics")],
            entity_id=None,
            captured_at=now,
        ),
        trace_id="trace_test_01",
        actor_id="operator_alice",
        created_at=now,
        updated_at=now,
    )
    step = Step(
        id="step_test_01",
        run_id="run_test_01",
        step_name=PipelineStage.RESEARCH.value,
        step_index=1,
        status=StepStatus.RUNNING,
        input_hash="hash_01",
        started_at=now,
    )

    # 1. Research stage passes real topic title in search query
    research_res = MagicMock()
    research_res.snapshots_created = ["snap_01"]
    mock_runner.research_agent.execute.return_value = research_res
    await mock_runner._dispatch_stage_handler(run, PipelineStage.RESEARCH, step)
    mock_runner.research_agent.execute.assert_awaited_once_with(
        topic_id="origin_of_mathematics",
        search_query="History of Ancient Mathematics primary history archive",
        limit=1,
    )

    # 2. Extraction stage passes real topic_title
    mock_runner._stage_output = AsyncMock(return_value="snap_01")
    extract_res = MagicMock()
    extract_res.claims_count = 5
    mock_runner.extraction_agent.execute.return_value = extract_res
    await mock_runner._dispatch_stage_handler(run, PipelineStage.CLAIM_EXTRACTION, step)
    mock_runner.extraction_agent.execute.assert_awaited_once_with(
        topic_id="origin_of_mathematics",
        topic_title="History of Ancient Mathematics",
        snapshot_id="snap_01",
        run_id="run_test_01",
        step_id="step_test_01",
    )

    # 3. Script generation stage passes real topic_title
    mock_runner.script_agent.select_story_angle.return_value = "archival_origins"
    script_mock = MagicMock()
    script_mock.script.id = "script_01"
    script_mock.timing_plan = MagicMock()
    mock_runner.script_agent.generate_script.return_value = script_mock
    await mock_runner._dispatch_stage_handler(run, PipelineStage.SCRIPT_GENERATION, step)
    mock_runner.script_agent.select_story_angle.assert_awaited_once_with(
        ko_id="ko_origin_of_mathematics",
        topic_title="History of Ancient Mathematics",
        run_id="run_test_01",
        step_id="step_test_01",
    )
    mock_runner.script_agent.generate_script.assert_awaited_once_with(
        ko_id="ko_origin_of_mathematics",
        topic_title="History of Ancient Mathematics",
        story_angle="archival_origins",
        run_id="run_test_01",
        step_id="step_test_01",
    )

    # 4. Quality check stage passes real topic_title
    mock_runner._load_script_and_timing = AsyncMock(
        return_value=(script_mock.script, script_mock.timing_plan)
    )
    eval_res = MagicMock()
    eval_res.passed = True
    eval_res.report.id = "report_01"
    mock_runner.judge_agent.evaluate_script.return_value = eval_res
    await mock_runner._dispatch_stage_handler(run, PipelineStage.QUALITY_CHECK, step)
    mock_runner.judge_agent.evaluate_script.assert_awaited_once_with(
        run_id="run_test_01",
        script=script_mock.script,
        timing_plan=script_mock.timing_plan,
        topic_title="History of Ancient Mathematics",
        step_id="step_test_01",
    )
