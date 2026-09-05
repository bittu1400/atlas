"""Gate Policy Evaluation.

As specified in SPEC §6 and Invariants 7 & 9:
- Stages are governed by Gate Policies: automatic, manual, or hybrid.
- AI-generated imagery ALWAYS requires explicit human approval (Invariant 9).
- Quality check is an automatic HARD GATE (SPEC §8.2).
"""

from atlas.domain.execution.models import GateType, PipelineStage

# Standard default gate policy per stage (SPEC §6)
DEFAULT_STAGE_GATES: dict[PipelineStage, GateType] = {
    PipelineStage.IDEA_DISCOVERY: GateType.AUTOMATIC,
    PipelineStage.TOPIC_SELECTION: GateType.MANUAL,
    PipelineStage.RESEARCH: GateType.AUTOMATIC,
    PipelineStage.CLAIM_EXTRACTION: GateType.AUTOMATIC,
    PipelineStage.FACT_VERIFICATION: GateType.HYBRID,
    PipelineStage.KNOWLEDGE_OBJECT: GateType.MANUAL,
    PipelineStage.STORY_ANGLE: GateType.HYBRID,
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
    ) -> tuple[bool, GateType]:
        """Determine if stage suspends and the resulting GateType."""
        gate_type = DEFAULT_STAGE_GATES.get(stage, GateType.AUTOMATIC)

        # Invariant 9: AI generated assets ALWAYS require manual approval
        if stage == PipelineStage.ASSET_SELECTION and has_ai_generated_assets:
            return True, GateType.MANUAL

        if gate_type == GateType.MANUAL:
            return True, GateType.MANUAL

        if gate_type == GateType.HYBRID:
            if stage == PipelineStage.FACT_VERIFICATION and has_contested_claims:
                return True, GateType.HYBRID
            if stage == PipelineStage.STORY_ANGLE:
                return True, GateType.HYBRID

        return False, gate_type
