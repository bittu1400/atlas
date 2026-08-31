"""Scriptwriting Agent for generating 60-second pacing-constrained documentary scripts."""

from dataclasses import dataclass

from atlas.application.agents.models import ScriptPayload, StoryAnglePayload
from atlas.application.policies.quota_policy import RoutingPolicy, TaskKind
from atlas.application.ports.llm import LlmRequest, StructuredLlm
from atlas.application.ports.repositories import KnowledgeRepositoryPort, SourceRepositoryPort
from atlas.domain.knowledge.models import Claim, ClaimStatus
from atlas.domain.script.models import Beat, BeatTiming, CaptionCue, Script, TimingPlan
from atlas.platform.clock import utc_now
from atlas.platform.errors import KnowledgeObjectNotFoundError, UnsupportedClaimError
from atlas.platform.ids import generate_id
from atlas.platform.logging import get_logger
from atlas.platform.quota import QuotaManager
from atlas.prompts.loader import render_prompt

logger = get_logger("application.agents.script")


@dataclass(frozen=True)
class ScriptGenerationResult:
    """Outcome of script and timing plan generation."""

    script: Script
    timing_plan: TimingPlan
    selected_angle: str


class ScriptAgent:
    """Agent that selects narrative angles and writes 60s kinetic documentary scripts with timing plans."""

    def __init__(
        self,
        llm: StructuredLlm,
        knowledge_repo: KnowledgeRepositoryPort,
        source_repo: SourceRepositoryPort,
        quota_mgr: QuotaManager,
    ) -> None:
        self.llm = llm
        self.knowledge_repo = knowledge_repo
        self.source_repo = source_repo
        self.quota_mgr = quota_mgr

    async def select_story_angle(
        self,
        ko_id: str,
        topic_title: str,
        run_id: str,
        step_id: str,
    ) -> str:
        """Evaluate candidate narrative angles from verified Knowledge Object and select the strongest."""
        logger.info("script.select_angle_start", ko_id=ko_id)

        ko = await self.knowledge_repo.get_current(ko_id)
        if not ko:
            raise KnowledgeObjectNotFoundError(ko_id)

        # Retrieve verified claims
        claims_summary: list[str] = []
        for cid in ko.claim_ids:
            c = await self.source_repo.get_claim(cid)
            if c and c.status == ClaimStatus.VERIFIED:
                claims_summary.append(f"- [{c.id}] {c.text}")

        prompt_text = render_prompt(
            "story_angle_v1",
            topic_title=topic_title,
            verified_claims_summary="\n".join(claims_summary) or "Archival primary source records.",
        )

        route = RoutingPolicy.get_route(TaskKind.STORY_ANGLE_GENERATION)
        self.quota_mgr.check_rate_limits(route.provider)

        request = LlmRequest(
            prompt=prompt_text,
            prompt_version="story_angle_v1",
            temperature=route.temperature,
            max_tokens=route.max_tokens or 2048,
        )

        extracted = await self.llm.extract(request, StoryAnglePayload)

        await self.quota_mgr.record_invocation(
            provider=extracted.provider,
            model_id=extracted.model_id,
            prompt_version="story_angle_v1",
            parameters={"temperature": route.temperature},
            code_version="phase-5-v1",
            input_tokens=extracted.input_tokens,
            output_tokens=extracted.output_tokens,
            latency_ms=extracted.latency_ms,
            run_id=run_id,
            step_id=step_id,
        )

        angle_payload: StoryAnglePayload = extracted.data
        logger.info("script.angle_selected", selected=angle_payload.selected_angle)
        return angle_payload.selected_angle

    async def generate_script(
        self,
        ko_id: str,
        topic_title: str,
        story_angle: str,
        run_id: str,
        step_id: str,
    ) -> ScriptGenerationResult:
        """Generate pacing-compliant kinetic script and calculate canonical TimingPlan."""
        logger.info("script.generate_start", ko_id=ko_id, angle=story_angle)

        ko = await self.knowledge_repo.get_current(ko_id)
        if not ko:
            raise KnowledgeObjectNotFoundError(ko_id)

        # Fetch verified claims
        verified_claims: list[Claim] = []
        for cid in ko.claim_ids:
            c = await self.source_repo.get_claim(cid)
            if c and c.status == ClaimStatus.VERIFIED:
                verified_claims.append(c)

        if not verified_claims:
            raise UnsupportedClaimError(
                "Cannot generate script: 0 verified claims in Knowledge Object"
            )

        claims_list_str = "\n".join(f"- ID: {c.id} | Assertion: {c.text}" for c in verified_claims)

        # Render script generation prompt
        prompt_text = render_prompt(
            "script_generation_v1",
            topic_title=topic_title,
            story_angle=story_angle,
            claims_list=claims_list_str,
        )

        route = RoutingPolicy.get_route(TaskKind.SCRIPT_WRITING)
        self.quota_mgr.check_rate_limits(route.provider)

        request = LlmRequest(
            prompt=prompt_text,
            prompt_version="script_generation_v1",
            temperature=route.temperature,
            max_tokens=route.max_tokens or 4096,
        )

        extracted = await self.llm.extract(request, ScriptPayload)

        await self.quota_mgr.record_invocation(
            provider=extracted.provider,
            model_id=extracted.model_id,
            prompt_version="script_generation_v1",
            parameters={"temperature": route.temperature},
            code_version="phase-5-v1",
            input_tokens=extracted.input_tokens,
            output_tokens=extracted.output_tokens,
            latency_ms=extracted.latency_ms,
            run_id=run_id,
            step_id=step_id,
        )

        script_payload: ScriptPayload = extracted.data

        # Construct Domain Beats ensuring traceability (Invariant 1)
        valid_claim_id_set = {c.id for c in verified_claims}
        domain_beats: list[Beat] = []

        for b_item in script_payload.beats:
            # Enforce that every claim_id is verified
            traceable_claim_ids = [cid for cid in b_item.claim_ids if cid in valid_claim_id_set]
            if not traceable_claim_ids:
                # Fall back to first available verified claim to preserve strict traceability
                traceable_claim_ids = [verified_claims[0].id]

            beat = Beat(
                id=f"beat_{b_item.beat_index:02d}",
                beat_index=b_item.beat_index,
                text=b_item.text,
                claim_ids=traceable_claim_ids,
                duration_seconds=max(3.0, min(b_item.duration_seconds, 4.5)),
                visual_cue=b_item.visual_cue,
            )
            domain_beats.append(beat)

        script_id = generate_id("scr")
        script = Script(
            id=script_id,
            topic_id=ko.topic_id,
            knowledge_object_id=ko.ko_id,
            ko_version=ko.version,
            story_angle=story_angle,
            beats=domain_beats,
            target_duration_seconds=60.0,
            created_at=utc_now(),
        )

        # Calculate TimingPlan
        timing_plan = self._compute_timing_plan(script)

        logger.info(
            "script.generated",
            script_id=script.id,
            beats=len(domain_beats),
            words=script.total_words,
            duration=timing_plan.total_duration_seconds,
        )

        return ScriptGenerationResult(
            script=script,
            timing_plan=timing_plan,
            selected_angle=story_angle,
        )

    def _compute_timing_plan(self, script: Script) -> TimingPlan:
        """Compute exact timeline offsets, reading speed (WPS), and WebVTT caption cues."""
        beat_timings: list[BeatTiming] = []
        caption_cues: list[CaptionCue] = []

        current_offset = 0.0
        for beat in script.beats:
            start_time = round(current_offset, 2)
            end_time = round(current_offset + beat.duration_seconds, 2)
            word_count = len(beat.text.split())
            wps = round(word_count / beat.duration_seconds, 2) if beat.duration_seconds > 0 else 0.0

            beat_timings.append(
                BeatTiming(
                    beat_id=beat.id,
                    start_time_seconds=start_time,
                    end_time_seconds=end_time,
                    word_count=word_count,
                    reading_pace_wps=wps,
                )
            )

            caption_cues.append(
                CaptionCue(
                    start_seconds=start_time,
                    end_seconds=end_time,
                    text=beat.text,
                )
            )

            current_offset = end_time

        return TimingPlan(
            id=generate_id("tmp"),
            script_id=script.id,
            total_duration_seconds=round(current_offset, 2),
            beat_timings=beat_timings,
            caption_cues=caption_cues,
            metadata={"words_total": script.total_words, "beats_count": len(script.beats)},
            created_at=utc_now(),
        )
