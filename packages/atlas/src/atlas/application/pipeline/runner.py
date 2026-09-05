"""Pipeline Stage Execution Engine and Handlers.

As specified in SPEC §6, ARCHITECTURE §3, and ADR-0001:
- State machine executes 18 discrete stages with idempotency checking and checkpointing.
- Suspension is a database row; worker exits immediately when a gate is reached.
- Quality gate enforces strict rubric scoring (>= 78 overall, >= 60 per dimension).
- Remotion render acquires the GPU lease from resource_locks.
"""

import hashlib

from atlas.application.agents.extraction import ExtractionAgent
from atlas.application.agents.judge import JudgeAgent
from atlas.application.agents.research import ResearchAgent
from atlas.application.agents.script import ScriptAgent
from atlas.application.agents.sound_design import SoundDesignAgent
from atlas.application.agents.storyboard import StoryboardAgent
from atlas.application.agents.topic import TopicDiscoveryAgent
from atlas.application.agents.verification import VerificationAgent
from atlas.application.policies.gate_policy import GatePolicy
from atlas.application.policies.license_policy import LicensePolicy
from atlas.application.ports.embedder import Embedder
from atlas.application.ports.llm import StructuredLlm
from atlas.application.ports.media import ImageGenerator, ImageSearch, SoundLibrary
from atlas.application.ports.notify import Notifier
from atlas.application.ports.publish import Publisher
from atlas.application.ports.renderer import Renderer
from atlas.application.ports.repositories import (
    ExecutionRepositoryPort,
    FocusRepositoryPort,
    KnowledgeRepositoryPort,
    ProductionRepositoryPort,
    PublishingRepositoryPort,
    SourceRepositoryPort,
)
from atlas.application.ports.search import Search
from atlas.application.ports.sources import SourceFetcher
from atlas.application.ports.storage import Storage
from atlas.domain.execution.models import (
    ApprovalDecision,
    Gate,
    GateStatus,
    IdempotencyKey,
    PipelineStage,
    Run,
    RunStatus,
    Step,
    StepStatus,
)
from atlas.domain.knowledge.models import AssertionType, Claim, ClaimStatus
from atlas.domain.script.models import Script, TimingPlan
from atlas.platform.clock import utc_now
from atlas.platform.errors import (
    ProductionArtifactNotFoundError,
    PublisherNotConfiguredError,
    QualityGateFailedError,
    StepExecutionError,
    StepNotFoundError,
    UnapprovedScriptError,
)
from atlas.platform.ids import (
    generate_gate_id,
    knowledge_object_id_for_topic,
)
from atlas.platform.logging import get_logger
from atlas.platform.quota import QuotaManager

logger = get_logger("application.pipeline")

STAGE_SEQUENCE: list[PipelineStage] = [
    PipelineStage.IDEA_DISCOVERY,
    PipelineStage.TOPIC_SELECTION,
    PipelineStage.RESEARCH,
    PipelineStage.CLAIM_EXTRACTION,
    PipelineStage.FACT_VERIFICATION,
    PipelineStage.KNOWLEDGE_OBJECT,
    PipelineStage.STORY_ANGLE,
    PipelineStage.SCRIPT_GENERATION,
    PipelineStage.SCRIPT_APPROVAL,
    PipelineStage.TIMING_PLAN,
    PipelineStage.ASSET_DISCOVERY,
    PipelineStage.ASSET_SELECTION,
    PipelineStage.STORYBOARD_CUTS,
    PipelineStage.SOUND_DESIGN,
    PipelineStage.REMOTION_RENDER,
    PipelineStage.QUALITY_CHECK,
    PipelineStage.FINAL_APPROVAL,
    PipelineStage.PUBLISH,
]


def _step_id(run_id: str, stage: PipelineStage) -> str:
    """Deterministic Step ID for a stage of a Run, so resumes address the same row."""
    return f"step_{run_id}_{stage.value}"


class PipelineRunner:
    """Orchestrates the durable, idempotent state machine across all 18 pipeline stages."""

    def __init__(
        self,
        execution_repo: ExecutionRepositoryPort,
        knowledge_repo: KnowledgeRepositoryPort,
        focus_repo: FocusRepositoryPort,
        source_repo: SourceRepositoryPort,
        publishing_repo: PublishingRepositoryPort,
        production_repo: ProductionRepositoryPort,
        storage: Storage,
        llm: StructuredLlm,
        embedder: Embedder,
        search: Search,
        source_fetcher: SourceFetcher,
        image_search: ImageSearch,
        image_gen: ImageGenerator,
        sound_lib: SoundLibrary,
        renderer: Renderer,
        notifier: Notifier,
        quota_mgr: QuotaManager,
        publisher: Publisher | None = None,
    ) -> None:
        self.execution_repo = execution_repo
        self.knowledge_repo = knowledge_repo
        self.focus_repo = focus_repo
        self.source_repo = source_repo
        self.publishing_repo = publishing_repo
        self.production_repo = production_repo
        self.storage = storage
        self.llm = llm
        self.embedder = embedder
        self.search = search
        self.source_fetcher = source_fetcher
        self.image_search = image_search
        self.image_gen = image_gen
        self.sound_lib = sound_lib
        self.renderer = renderer
        self.notifier = notifier
        self.quota_mgr = quota_mgr
        self.publisher = publisher
        self.research_agent = ResearchAgent(
            search=self.search,
            source_fetcher=self.source_fetcher,
            storage=self.storage,
            source_repo=self.source_repo,
        )
        self.extraction_agent = ExtractionAgent(
            llm=self.llm,
            storage=self.storage,
            source_repo=self.source_repo,
            knowledge_repo=self.knowledge_repo,
            quota_mgr=self.quota_mgr,
        )
        self.verification_agent = VerificationAgent(
            llm=self.llm,
            source_repo=self.source_repo,
            quota_mgr=self.quota_mgr,
        )
        self.script_agent = ScriptAgent(
            llm=self.llm,
            knowledge_repo=self.knowledge_repo,
            source_repo=self.source_repo,
            quota_mgr=self.quota_mgr,
        )
        self.judge_agent = JudgeAgent(
            llm=self.llm,
            quota_mgr=self.quota_mgr,
        )
        self.topic_agent = TopicDiscoveryAgent(llm=self.llm, quota_mgr=self.quota_mgr)
        self.storyboard_agent = StoryboardAgent(embedder=self.embedder, quota_mgr=self.quota_mgr)
        self.sound_design_agent = SoundDesignAgent(sound_library=self.sound_lib)

    async def run_pipeline(self, run_id: str) -> Run:
        """Advance the pipeline for a Run until completion or a suspension Gate is encountered."""
        run = await self.execution_repo.get_run(run_id)

        if run.status in {RunStatus.COMPLETED, RunStatus.ABANDONED, RunStatus.FAILED}:
            logger.info("pipeline.already_terminal", run_id=run_id, status=run.status)
            return run

        if run.status == RunStatus.PENDING:
            await self.execution_repo.update_run_status(run.id, RunStatus.RUNNING)
            run = await self.execution_repo.get_run(run_id)

        for index, stage in enumerate(STAGE_SEQUENCE, start=1):
            should_suspend, gate = await self._execute_stage(run, stage, index)
            if should_suspend:
                logger.info(
                    "pipeline.suspended_at_gate",
                    run_id=run.id,
                    stage=stage,
                    gate_id=gate.id if gate else None,
                )
                await self.execution_repo.update_run_status(run.id, RunStatus.SUSPENDED)
                await self.notifier.notify(
                    "gate_suspension",
                    f"Run '{run.id}' suspended at gate for stage '{stage.value}'",
                    {"run_id": run.id, "stage": stage.value, "gate_id": gate.id if gate else None},
                )
                return await self.execution_repo.get_run(run_id)

        # All stages completed
        now = utc_now()
        await self.execution_repo.update_run_status(run.id, RunStatus.COMPLETED, completed_at=now)
        logger.info("pipeline.completed_successfully", run_id=run.id)
        await self.notifier.notify(
            "run_completed",
            f"Run '{run.id}' completed all 18 stages successfully",
            {"run_id": run.id},
        )
        return await self.execution_repo.get_run(run_id)

    async def _execute_stage(
        self, run: Run, stage: PipelineStage, stage_index: int
    ) -> tuple[bool, Gate | None]:
        """Execute or retrieve cached step for a stage, creating suspension gates as needed."""
        step_id = _step_id(run.id, stage)
        input_hash = hashlib.sha256(
            f"{run.id}:{stage.value}:{run.captured_focus.focus_id}".encode()
        ).hexdigest()
        idempotency_key_str = f"{run.id}:{stage.value}:{input_hash}"

        # 1. Check Idempotency Key
        existing_key = await self.execution_repo.get_idempotency_key(idempotency_key_str)
        if existing_key:
            logger.info("step.idempotency_cache_hit", run_id=run.id, stage=stage.value)
            # Ensure step exists in DB
            try:
                await self.execution_repo.get_step(step_id)
            except StepNotFoundError:
                await self.execution_repo.create_step(
                    Step(
                        id=step_id,
                        run_id=run.id,
                        step_name=stage.value,
                        step_index=stage_index,
                        status=StepStatus.SUCCEEDED,
                        input_hash=input_hash,
                        output_artifact_ref=existing_key.output_hash,
                        started_at=utc_now(),
                        completed_at=utc_now(),
                    )
                )
            return False, None

        # 2. Check if a Gate for this step already exists
        gates_for_run = await self.execution_repo.list_gates_for_run(run.id)
        existing_gate = next((g for g in gates_for_run if g.step_id == step_id), None)

        if existing_gate:
            if existing_gate.status == GateStatus.APPROVED:
                # Gate was already approved by operator -> complete step and continue
                await self.execution_repo.update_step(
                    step_id=step_id,
                    status=StepStatus.SUCCEEDED,
                    output_artifact_ref=f"approved_gate_{existing_gate.id}",
                    completed_at=utc_now(),
                )
                gate_out_hash = hashlib.sha256(
                    f"approved_gate_{existing_gate.id}".encode()
                ).hexdigest()
                await self.execution_repo.record_idempotency_key(
                    IdempotencyKey(
                        key=idempotency_key_str,
                        step_id=step_id,
                        output_hash=gate_out_hash,
                        created_at=utc_now(),
                    )
                )
                return False, None
            elif existing_gate.status == GateStatus.PENDING:
                # Still waiting for operator approval
                return True, existing_gate
            elif existing_gate.status == GateStatus.REJECTED:
                # Gate was rejected; keep run suspended/reworking
                return True, existing_gate

        # 3. Evaluate Gate Policy
        has_contested_claims = False
        if stage in {
            PipelineStage.FACT_VERIFICATION,
            PipelineStage.KNOWLEDGE_OBJECT,
            PipelineStage.STORY_ANGLE,
        }:
            ko = await self.knowledge_repo.get_current_for_topic(run.topic_id)
            if ko and ko.claim_ids:
                for cid in ko.claim_ids:
                    clm = await self.source_repo.get_claim(cid)
                    if clm and (
                        clm.status == ClaimStatus.CONTESTED
                        or clm.assertion_type == AssertionType.CONTESTED
                    ):
                        has_contested_claims = True
                        break

        has_ai_generated_assets = False
        if stage == PipelineStage.ASSET_SELECTION:
            steps = await self.execution_repo.list_steps_for_run(run.id)
            for s in steps:
                if s.step_name == PipelineStage.ASSET_DISCOVERY.value and s.status == "succeeded":
                    if s.output_artifact_ref and "_ai" in s.output_artifact_ref:
                        has_ai_generated_assets = True
                    break

        should_suspend, gate_type = GatePolicy.should_suspend(
            stage=stage,
            has_contested_claims=has_contested_claims,
            has_ai_generated_assets=has_ai_generated_assets,
        )
        if should_suspend:
            # Create Step as suspended
            step = Step(
                id=step_id,
                run_id=run.id,
                step_name=stage.value,
                step_index=stage_index,
                status=StepStatus.SUSPENDED,
                input_hash=input_hash,
                started_at=utc_now(),
            )
            await self.execution_repo.create_step(step)

            # Create Gate row
            gate = Gate(
                id=generate_gate_id(),
                run_id=run.id,
                step_id=step.id,
                gate_type=gate_type,
                status=GateStatus.PENDING,
                requested_at=utc_now(),
            )
            await self.execution_repo.create_gate(gate)
            return True, gate

        # 3. Create active Step
        step = Step(
            id=step_id,
            run_id=run.id,
            step_name=stage.value,
            step_index=stage_index,
            status=StepStatus.RUNNING,
            input_hash=input_hash,
            started_at=utc_now(),
        )
        await self.execution_repo.create_step(step)

        try:
            # 4. Dispatch Stage Handler
            output_ref = await self._dispatch_stage_handler(run, stage, step)

            # 5. Checkpoint Step
            now = utc_now()
            await self.execution_repo.update_step(
                step_id=step.id,
                status=StepStatus.SUCCEEDED,
                output_artifact_ref=output_ref,
                completed_at=now,
            )

            # 6. Record Idempotency Key
            out_hash = hashlib.sha256((output_ref or "success").encode()).hexdigest()
            await self.execution_repo.record_idempotency_key(
                IdempotencyKey(
                    key=idempotency_key_str,
                    step_id=step.id,
                    output_hash=out_hash,
                    created_at=now,
                )
            )

            return False, None
        except Exception as exc:
            now = utc_now()
            err_msg = str(exc)
            await self.execution_repo.update_step(
                step_id=step.id,
                status=StepStatus.FAILED,
                error=err_msg,
                completed_at=now,
            )
            await self.execution_repo.update_run_status(
                run.id,
                RunStatus.FAILED,
                completed_at=now,
                error=err_msg,
            )
            logger.error("stage.failed", stage=stage.value, run_id=run.id, error=err_msg)
            raise StepExecutionError(step_name=stage.value, reason=err_msg) from exc

    async def _stage_output(self, run_id: str, stage: PipelineStage) -> str:
        """Return the artifact reference a completed earlier stage checkpointed.

        Downstream stages read what upstream stages produced instead of
        regenerating it; a regenerated artifact is not the one the operator
        approved (Invariant 7).
        """
        steps = await self.execution_repo.list_steps_for_run(run_id)
        for candidate in steps:
            if candidate.step_name == stage.value and candidate.output_artifact_ref:
                return candidate.output_artifact_ref
        raise ProductionArtifactNotFoundError(f"Output of stage '{stage.value}'", run_id)

    async def _load_script_and_timing(self, run_id: str) -> tuple[Script, TimingPlan]:
        """Load the persisted Script approved at stage 9 and its canonical TimingPlan."""
        script_id = await self._stage_output(run_id, PipelineStage.SCRIPT_GENERATION)
        script = await self.production_repo.get_script(script_id)
        timing_plan = await self.production_repo.get_timing_plan_for_script(script_id)
        return script, timing_plan

    async def _asset_selection_was_approved_by_a_human(self, run_id: str) -> bool:
        """Report whether a person recorded an approval on this Run's asset-selection gate.

        Invariant 9 asks for an explicit human decision, so this looks for an
        Approval row by the deciding actor, not merely a gate row whose status
        column reads `approved`.
        """
        target_step_id = _step_id(run_id, PipelineStage.ASSET_SELECTION)
        gates = await self.execution_repo.list_gates_for_run(run_id)
        gate_ids = {g.id for g in gates if g.step_id == target_step_id}
        if not gate_ids:
            return False
        approvals = await self.execution_repo.list_approvals_for_run(run_id)
        return any(
            a.gate_id in gate_ids and a.decision == ApprovalDecision.APPROVED for a in approvals
        )

    async def _assert_script_claims_are_traceable(self, script: Script) -> None:
        """Refuse to render a Script whose beats cite claims that are not verified with evidence.

        This is the last check before bytes leave the system (Invariants 1 & 2):
        it runs against the persisted Script, so it validates what will actually
        be rendered rather than a freshly generated stand-in.
        """
        offenders: set[str] = set()
        for beat in script.beats:
            for claim_id in beat.claim_ids:
                claim = await self.source_repo.get_claim(claim_id)
                if claim is None or claim.status != ClaimStatus.VERIFIED:
                    offenders.add(claim_id)
                    continue
                chain = await self.knowledge_repo.get_traceability_chain(claim_id)
                if not chain.evidence_with_sources:
                    offenders.add(claim_id)
        if offenders:
            raise UnapprovedScriptError(script.id, sorted(offenders))

    async def _resolve_topic_title(self, topic_id: str) -> str:
        """Fetch the Topic row and return its human-readable title, falling back to topic_id."""
        topic = await self.source_repo.get_topic(topic_id)
        if topic is not None and topic.title:
            return topic.title
        return topic_id

    async def _dispatch_stage_handler(self, run: Run, stage: PipelineStage, step: Step) -> str:
        """Execute domain logic for a specific automated stage."""
        logger.info("stage.executing", stage=stage.value, run_id=run.id)
        topic_title = await self._resolve_topic_title(run.topic_id)

        if stage == PipelineStage.IDEA_DISCOVERY:
            ideas = await self.topic_agent.execute(
                run.captured_focus, run_id=run.id, step_id=step.id
            )
            return f"ideas_count_{len(ideas)}"

        elif stage == PipelineStage.RESEARCH:
            # Fetch Tier 0 primary sources and snapshot content via ResearchAgent
            result = await self.research_agent.execute(
                topic_id=run.topic_id,
                search_query=f"{topic_title} primary history archive",
                limit=1,
            )
            if not result.snapshots_created:
                raise ProductionArtifactNotFoundError("Snapshot for topic", run.topic_id)
            return result.snapshots_created[0]

        elif stage == PipelineStage.CLAIM_EXTRACTION:
            # Extract from the snapshot the research stage already fetched; refetching
            # would hit the network twice and could extract from different bytes.
            snapshot_id = await self._stage_output(run.id, PipelineStage.RESEARCH)
            extract_result = await self.extraction_agent.execute(
                topic_id=run.topic_id,
                topic_title=topic_title,
                snapshot_id=snapshot_id,
                run_id=run.id,
                step_id=step.id,
            )
            return f"extracted_claims_{extract_result.claims_count}"

        elif stage == PipelineStage.FACT_VERIFICATION:
            ko = await self.knowledge_repo.get_current_for_topic(run.topic_id)
            if ko and ko.claim_ids:
                for cid in ko.claim_ids:
                    chain = await self.knowledge_repo.get_traceability_chain(cid)
                    if not chain.evidence_with_sources:
                        claim = chain.claim
                        unsupported_claim = Claim(
                            id=claim.id,
                            text=claim.text,
                            assertion_type=claim.assertion_type,
                            confidence=claim.confidence,
                            status=ClaimStatus.UNSUPPORTED,
                            inferred_from_claim_ids=list(claim.inferred_from_claim_ids),
                            created_at=claim.created_at,
                        )
                        await self.source_repo.save_claim(
                            unsupported_claim,
                            actor_id="agent.verification",
                            reason="No evidence link survived extraction",
                        )
                        continue

                    for _link, evidence, _src, _snp in chain.evidence_with_sources:
                        await self.verification_agent.verify_claim(
                            claim_id=cid,
                            evidence_id=evidence.id,
                            run_id=run.id,
                            step_id=step.id,
                        )
            return "all_claims_verified"

        elif stage == PipelineStage.SCRIPT_GENERATION:
            ko_id = knowledge_object_id_for_topic(run.topic_id)
            story_angle = await self.script_agent.select_story_angle(
                ko_id=ko_id,
                topic_title=topic_title,
                run_id=run.id,
                step_id=step.id,
            )
            script_res = await self.script_agent.generate_script(
                ko_id=ko_id,
                topic_title=topic_title,
                story_angle=story_angle,
                run_id=run.id,
                step_id=step.id,
            )
            await self.production_repo.save_script(script_res.script, run.id)
            await self.production_repo.save_timing_plan(script_res.timing_plan, run.id)
            return script_res.script.id

        elif stage == PipelineStage.TIMING_PLAN:
            # The plan was computed with the script; this stage validates and
            # publishes its ID, it does not call a model again.
            _script, timing_plan = await self._load_script_and_timing(run.id)
            return timing_plan.id

        elif stage == PipelineStage.ASSET_DISCOVERY:
            candidates = await self.image_search.search_archival(topic_title, limit=10)
            has_ai = False
            for c in candidates:
                LicensePolicy.validate_asset_license(c.id, c.license_id)
                if c.is_ai_generated:
                    has_ai = True
            return f"assets_found_{len(candidates)}{'_ai' if has_ai else ''}"

        elif stage == PipelineStage.STORYBOARD_CUTS:
            script, timing_plan = await self._load_script_and_timing(run.id)
            candidates = await self.image_search.search_archival(
                topic_title, limit=max(5, len(script.beats))
            )
            if not candidates:
                raise ProductionArtifactNotFoundError("Archival assets for topic", run.topic_id)

            is_human_approved = await self._asset_selection_was_approved_by_a_human(run.id)
            for c in candidates:
                LicensePolicy.validate_asset_license(c.id, c.license_id)
                if c.is_ai_generated:
                    LicensePolicy.validate_ai_image_approval(
                        c.id, is_human_approved=is_human_approved
                    )

            storyboard = await self.storyboard_agent.generate(
                script, timing_plan, candidates, run_id=run.id, step_id=step.id
            )
            await self.production_repo.save_storyboard(storyboard, run.id)
            return storyboard.id

        elif stage == PipelineStage.SOUND_DESIGN:
            storyboard_id = await self._stage_output(run.id, PipelineStage.STORYBOARD_CUTS)
            storyboard = await self.production_repo.get_storyboard(storyboard_id)
            timing_plan = await self.production_repo.get_timing_plan(storyboard.timing_plan_id)
            soundtrack = await self.sound_design_agent.compose(storyboard.id, timing_plan)
            return soundtrack.id

        elif stage == PipelineStage.REMOTION_RENDER:
            storyboard_id = await self._stage_output(run.id, PipelineStage.STORYBOARD_CUTS)
            storyboard = await self.production_repo.get_storyboard(storyboard_id)
            script = await self.production_repo.get_script(storyboard.script_id)
            timing_plan = await self.production_repo.get_timing_plan(storyboard.timing_plan_id)

            # Pre-output invariant backstop (Invariants 1 & 2, defect D-06)
            await self._assert_script_claims_are_traceable(script)

            # Acquire GPU Semaphore Lease (ADR-0001)
            holder_id = f"worker_{run.id}"
            await self.execution_repo.acquire_lock("gpu", holder_id=holder_id, ttl_seconds=60)
            try:
                artifact_ids: list[str] = []
                for target in storyboard.render_targets:
                    artifact = await self.renderer.render(storyboard, timing_plan, target, run.id)
                    await self.production_repo.save_render_artifact(artifact)
                    artifact_ids.append(artifact.id)
                return ",".join(artifact_ids)
            finally:
                # Release GPU Semaphore Lease cleanly
                await self.execution_repo.release_lock("gpu", holder_id=holder_id)

        elif stage == PipelineStage.QUALITY_CHECK:
            script, timing_plan = await self._load_script_and_timing(run.id)
            eval_result = await self.judge_agent.evaluate_script(
                run_id=run.id,
                script=script,
                timing_plan=timing_plan,
                topic_title=topic_title,
                step_id=step.id,
            )
            if not eval_result.passed:
                raise QualityGateFailedError(
                    eval_result.weighted_score,
                    "; ".join(eval_result.rejection_reasons) or "Failed quality criteria",
                )
            return eval_result.report.id

        elif stage == PipelineStage.PUBLISH:
            if self.publisher is None:
                raise PublisherNotConfiguredError(run.id)
            artifacts = await self.production_repo.list_render_artifacts(run.id)
            if not artifacts:
                raise ProductionArtifactNotFoundError("RenderArtifact for run", run.id)
            script = await self.production_repo.get_script(
                (await self.production_repo.get_storyboard(artifacts[0].storyboard_id)).script_id
            )
            published_ids: list[str] = []
            for artifact in artifacts:
                external_id = await self.publisher.publish(
                    artifact,
                    run.channel_id,
                    {
                        "run_id": run.id,
                        "topic_id": run.topic_id,
                        "story_angle": script.story_angle,
                        "render_target": artifact.render_target.value,
                    },
                )
                published_ids.append(external_id)
            return ",".join(published_ids)

        elif stage in {
            PipelineStage.TOPIC_SELECTION,
            PipelineStage.KNOWLEDGE_OBJECT,
            PipelineStage.STORY_ANGLE,
            PipelineStage.SCRIPT_APPROVAL,
            PipelineStage.ASSET_SELECTION,
            PipelineStage.FINAL_APPROVAL,
        }:
            # Manual / Hybrid gate stages dispatched directly without suspension
            return f"gate_passed_{stage.value}"

        raise NotImplementedError(f"No stage handler implemented for stage '{stage.value}'")
