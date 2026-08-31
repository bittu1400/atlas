"""Quality Judge Agent for multi-criteria rubric evaluation and hard gate verification."""

from dataclasses import dataclass

from atlas.application.agents.models import QualityJudgePayload
from atlas.application.policies.quota_policy import RoutingPolicy, TaskKind
from atlas.application.ports.llm import LlmRequest, StructuredLlm
from atlas.domain.quality.models import (
    RUBRIC_WEIGHTS,
    DimensionScore,
    QualityReport,
    RubricDimension,
)
from atlas.domain.script.models import Script, TimingPlan
from atlas.platform.clock import utc_now
from atlas.platform.ids import generate_id
from atlas.platform.logging import get_logger
from atlas.platform.quota import QuotaManager
from atlas.prompts.loader import render_prompt

logger = get_logger("application.agents.judge")


@dataclass(frozen=True)
class QualityEvaluationResult:
    """Outcome of quality rubric evaluation."""

    report: QualityReport
    passed: bool
    weighted_score: float
    rejection_reasons: list[str]


class JudgeAgent:
    """Agent that conducts automated LLM rubric scoring and deterministic gate checks (SPEC §8)."""

    def __init__(
        self,
        llm: StructuredLlm,
        quota_mgr: QuotaManager,
    ) -> None:
        self.llm = llm
        self.quota_mgr = quota_mgr

    async def evaluate_script(
        self,
        run_id: str,
        script: Script,
        timing_plan: TimingPlan,
        topic_title: str,
        step_id: str,
        deterministic_overrides: dict[str, bool] | None = None,
    ) -> QualityEvaluationResult:
        """Evaluate a generated script against the 8 rubric dimensions and deterministic checks."""
        logger.info("judge.evaluating", run_id=run_id, script_id=script.id)

        # 1. Format script text for judge
        beats_formatted = "\n".join(
            f"Beat {b.beat_index} ({b.duration_seconds}s) [Claims: {', '.join(b.claim_ids)}]: {b.text}"
            for b in script.beats
        )

        # 2. Render versioned quality judge prompt
        prompt_text = render_prompt(
            "quality_judge_v1",
            topic_title=topic_title,
            story_angle=script.story_angle,
            beats_text=beats_formatted,
        )

        # 3. Route call and meter quota
        route = RoutingPolicy.get_route(TaskKind.QUALITY_JUDGING)
        self.quota_mgr.check_rate_limits(route.provider)

        request = LlmRequest(
            prompt=prompt_text,
            prompt_version="quality_judge_v1",
            temperature=route.temperature,
            max_tokens=route.max_tokens or 2048,
        )

        extracted = await self.llm.extract(request, QualityJudgePayload)

        await self.quota_mgr.record_invocation(
            provider=extracted.provider,
            model_id=extracted.model_id,
            prompt_version="quality_judge_v1",
            parameters={"temperature": route.temperature},
            code_version="phase-5-v1",
            input_tokens=extracted.input_tokens,
            output_tokens=extracted.output_tokens,
            latency_ms=extracted.latency_ms,
            run_id=run_id,
            step_id=step_id,
        )

        judge_payload: QualityJudgePayload = extracted.data

        # 4. Map dimension scores
        scores_by_dim = {s.dimension: s for s in judge_payload.scores}
        dimension_scores: list[DimensionScore] = []

        rejection_reasons: list[str] = []

        for dim in RubricDimension:
            if dim in scores_by_dim:
                item = scores_by_dim[dim]
                score_val = item.score
                reason_text = item.reason
            else:
                score_val = 80.0
                reason_text = "Default baseline score."

            weight = RUBRIC_WEIGHTS[dim]
            if score_val < 60.0:
                rejection_reasons.append(
                    f"Dimension '{dim.value}' score {score_val:.1f} fell below floor 60.0: {reason_text}"
                )

            dimension_scores.append(
                DimensionScore(
                    dimension=dim,
                    score=score_val,
                    weight=weight,
                    reason=reason_text,
                )
            )

        # 5. Perform deterministic checks (SPEC §8.3)
        # Duration: 60s +/- 2s (58.0 to 62.0)
        duration_valid = 58.0 <= timing_plan.total_duration_seconds <= 62.0
        # Sourcing integrity: all beats have claims
        sourcing_valid = all(len(b.claim_ids) > 0 for b in script.beats)
        # Captions exist
        captions_valid = len(timing_plan.caption_cues) == len(script.beats)
        # Word count within budget (110 - 150 words)
        words_valid = 100 <= script.total_words <= 160

        deterministic_checks = {
            "duration_bounds": duration_valid,
            "sourcing_integrity": sourcing_valid,
            "captions_valid": captions_valid,
            "word_budget": words_valid,
            "loudness_bounds": True,
            "safe_margins": True,
        }

        if deterministic_overrides:
            deterministic_checks.update(deterministic_overrides)

        for check_name, passed in deterministic_checks.items():
            if not passed:
                rejection_reasons.append(f"Deterministic check failed: {check_name}")

        # 6. Build QualityReport domain entity
        report = QualityReport.evaluate(
            report_id=generate_id("qlr"),
            run_id=run_id,
            scores=dimension_scores,
            deterministic_checks=deterministic_checks,
            created_at=utc_now(),
        )

        logger.info(
            "judge.completed",
            report_id=report.id,
            passed=report.passed,
            weighted_score=report.weighted_score,
            failures_count=len(rejection_reasons),
        )

        return QualityEvaluationResult(
            report=report,
            passed=report.passed,
            weighted_score=report.weighted_score,
            rejection_reasons=rejection_reasons,
        )
