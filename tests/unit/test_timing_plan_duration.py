"""Task T-20 / defect R-04: a Timing Plan's duration is derived, never defaulted.

`TimingPlan.total_duration_seconds` used to default to `60.0`. A plan built
without that field therefore reported a full minute with 3.5 seconds of beats
behind it, and sailed through the judge's 58-62 s deterministic check — a check
a default can satisfy is not a check. The value is now computed from the beat
timings, so no caller can construct a plan whose stated duration disagrees with
its own timeline.
"""

import pytest
from atlas.adapters.fakes.providers import FakeLlm
from atlas.application.agents.judge import JudgeAgent
from atlas.domain.script.models import Beat, BeatTiming, CaptionCue, Script, TimingPlan
from atlas.platform.clock import utc_now
from atlas.platform.quota import QuotaManager

from tests.unit.test_agents import InMemoryExecutionRepository


def _short_timing_plan(**overrides: float) -> TimingPlan:
    """A plan whose single beat occupies 3.5 seconds and nothing more."""
    return TimingPlan(
        id="tmp_t20",
        script_id="scr_t20",
        beat_timings=[
            BeatTiming(
                beat_id="beat_01",
                start_time_seconds=0.0,
                end_time_seconds=3.5,
                word_count=7,
                reading_pace_wps=2.0,
            )
        ],
        caption_cues=[CaptionCue(start_seconds=0.0, end_seconds=3.5, text="SUBJECT_A appears.")],
        created_at=utc_now(),
        **overrides,  # type: ignore[arg-type]
    )


def test_total_duration_is_derived_from_the_beat_timings() -> None:
    assert _short_timing_plan().total_duration_seconds == 3.5


def test_a_supplied_total_duration_cannot_override_the_beat_timings() -> None:
    """The field is computed, so a caller passing 60.0 does not get 60.0."""
    assert _short_timing_plan(total_duration_seconds=60.0).total_duration_seconds == 3.5


@pytest.mark.asyncio
async def test_the_deterministic_duration_check_rejects_a_short_plan() -> None:
    """The 58-62 s bound is what the default used to satisfy for free."""
    script = Script(
        id="scr_t20",
        topic_id="topic_t20",
        knowledge_object_id="ko_t20",
        ko_version=1,
        story_angle="PLACEHOLDER_ANGLE_ALPHA",
        beats=[
            Beat(
                id="beat_01",
                beat_index=1,
                text="SUBJECT_A appears.",
                claim_ids=["claim_01"],
                duration_seconds=3.5,
            )
        ],
        created_at=utc_now(),
    )
    exec_repo = InMemoryExecutionRepository()
    judge = JudgeAgent(
        llm=FakeLlm(),
        quota_mgr=QuotaManager(execution_repo=exec_repo),  # type: ignore[arg-type]
    )

    result = await judge.evaluate_script(
        run_id="run_t20",
        script=script,
        timing_plan=_short_timing_plan(),
        topic_title="Timing Plan Duration",
        step_id="step_t20",
    )

    assert result.report is not None
    assert result.report.deterministic_checks["duration_bounds"] is False
    assert result.passed is False
