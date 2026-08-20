"""Gate Policy Evaluation.

As specified in SPEC §6 and Invariants 7 & 9:
- Stages are governed by Gate Policies: automatic, manual, or hybrid.
- AI-generated imagery ALWAYS requires explicit human approval (Invariant 9).
- Quality check is an automatic HARD GATE (SPEC §8.2).
"""

from enum import StrEnum

from atlas.domain.execution.models import GateType


class PipelineStage(StrEnum):
    """The 17 stages in the Atlas production pipeline (SPEC §6)."""

    IDEA_DISCOVERY = "idea_discovery"  # Stage 1
    TOPIC_SELECTION = "topic_selection"  # Gate 2 (Manual)
    RESEARCH = "research"  # Stage 3
    CLAIM_EXTRACTION = "claim_extraction"  # Stage 4
    FACT_VERIFICATION = "fact_verification"  # Stage 5 (Hybrid)
    KNOWLEDGE_OBJECT = "knowledge_object"  # Gate 6 (Manual)
    STORY_ANGLE = "story_angle"  # Stage 7 (Hybrid)
    SCRIPT_GENERATION = "script_generation"  # Stage 8
    SCRIPT_APPROVAL = "script_approval"  # Gate 9 (Manual)
    TIMING_PLAN = "timing_plan"  # Stage 10
    ASSET_DISCOVERY = "asset_discovery"  # Stage 11
    ASSET_SELECTION = "asset_selection"  # Gate 12 (Manual)
    STORYBOARD_CUTS = "storyboard_cuts"  # Stage 13
    SOUND_DESIGN = "sound_design"  # Stage 14
    REMOTION_RENDER = "remotion_render"  # Stage 15
    QUALITY_CHECK = "quality_check"  # Stage 16 (Hard automatic gate)
    FINAL_APPROVAL = "final_approval"  # Gate 17 (Manual)
    PUBLISH = "publish"  # Stage 18 (Terminal publish ready)


# Standard default gate policy per stage
DEFAULT_STAGE_GATES: dict[PipelineStage, GateType] = {
    PipelineStage.IDEA_DISCOVERY: GateType.AUTOMATIC,
    PipelineStage.TOPIC_SELECTION: GateType.MANUAL,
    PipelineStage.RESEARCH: GateType.AUTOMATIC,
    PipelineStage.CLAIM_EXTRACTION: GateType.AUTOMATIC,
    PipelineStage.FACT_VERIFICATION: GateType.AUTOMATIC,
    PipelineStage.KNOWLEDGE_OBJECT: GateType.MANUAL,
    PipelineStage.STORY_ANGLE: GateType.AUTOMATIC,
    PipelineStage.SCRIPT_GENERATION: GateType.AUTOMATIC,
    PipelineStage.SCRIPT_APPROVAL: GateType.MANUAL,
    PipelineStage.TIMING_PLAN: GateType.AUTOMATIC,
    PipelineStage.ASSET_DISCOVERY: GateType.AUTOMATIC,
    PipelineStage.ASSET_SELECTION: GateType.MANUAL,
    PipelineStage.STORYBOARD_CUTS: GateType.AUTOMATIC,
    PipelineStage.SOUND_DESIGN: GateType.AUTOMATIC,
    PipelineStage.REMOTION_RENDER: GateType.AUTOMATIC,
    PipelineStage.QUALITY_CHECK: GateType.AUTOMATIC,
    PipelineStage.FINAL_APPROVAL: GateType.MANUAL,
    PipelineStage.PUBLISH: GateType.AUTOMATIC,
}


class GatePolicy:
    """Evaluates whether a stage should suspend for operator review."""

    @staticmethod
    def should_suspend(
        stage: PipelineStage,
        has_contested_claims: bool = False,
        has_ai_generated_assets: bool = False,
        policy_override: GateType | None = None,
    ) -> tuple[bool, GateType]:
        """Determine if stage suspends and the resulting GateType."""
        gate_type = policy_override or DEFAULT_STAGE_GATES.get(stage, GateType.AUTOMATIC)

        # Invariant 9: AI generated assets ALWAYS require manual approval
        if stage == PipelineStage.ASSET_SELECTION and has_ai_generated_assets:
            return True, GateType.MANUAL

        if gate_type == GateType.MANUAL:
            return True, GateType.MANUAL

        if (
            gate_type == GateType.HYBRID
            and stage == PipelineStage.FACT_VERIFICATION
            and has_contested_claims
        ):
            return True, GateType.HYBRID

        return False, gate_type
