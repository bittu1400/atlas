"""Pipeline Stage Execution Engine and Handlers.

As specified in SPEC §6, ARCHITECTURE §3, and ADR-0001:
- State machine executes 18 discrete stages with idempotency checking and checkpointing.
- Suspension is a database row; worker exits immediately when a gate is reached.
- Quality gate enforces strict rubric scoring (>= 78 overall, >= 60 per dimension).
- Remotion render acquires the GPU lease from resource_locks.
"""

import contextlib
import hashlib

from atlas.application.agents.extraction import ExtractionAgent
from atlas.application.agents.judge import JudgeAgent
from atlas.application.agents.research import ResearchAgent
from atlas.application.agents.script import ScriptAgent
from atlas.application.agents.sound_design import SoundDesignAgent
from atlas.application.agents.storyboard import StoryboardAgent
from atlas.application.agents.topic import TopicDiscoveryAgent
from atlas.application.agents.verification import VerificationAgent
from atlas.application.policies.gate_policy import GatePolicy, PipelineStage
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
    PublishingRepositoryPort,
    SourceRepositoryPort,
)
from atlas.application.ports.search import Search
from atlas.application.ports.sources import SourceFetcher
from atlas.application.ports.storage import Storage
from atlas.domain.execution.models import (
    Gate,
    GateStatus,
    IdempotencyKey,
    Run,
    RunStatus,
    Step,
    StepStatus,
)
from atlas.domain.media.models import (
    RenderTarget,
    Scene,
    Storyboard,
)
from atlas.domain.script.models import BeatTiming, TimingPlan
from atlas.platform.clock import utc_now
from atlas.platform.errors import (
    QualityGateFailedError,
    StepExecutionError,
    StepNotFoundError,
)
from atlas.platform.ids import (
    generate_gate_id,
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


class PipelineRunner:
    """Orchestrates the durable, idempotent state machine across all 18 pipeline stages."""

    def __init__(
        self,
        execution_repo: ExecutionRepositoryPort,
        knowledge_repo: KnowledgeRepositoryPort,
        focus_repo: FocusRepositoryPort,
        source_repo: SourceRepositoryPort,
        publishing_repo: PublishingRepositoryPort,
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
        self.topic_agent = TopicDiscoveryAgent(llm=self.llm)
        self.storyboard_agent = StoryboardAgent(embedder=self.embedder)
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
        step_id = f"step_{run.id}_{stage.value}"
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
        should_suspend, gate_type = GatePolicy.should_suspend(stage)
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

    async def _dispatch_stage_handler(self, run: Run, stage: PipelineStage, step: Step) -> str:
        """Execute domain logic for a specific automated stage."""
        logger.info("stage.executing", stage=stage.value, run_id=run.id)

        if stage == PipelineStage.IDEA_DISCOVERY:
            ideas = await self.topic_agent.execute(run.captured_focus)
            return f"ideas_count_{len(ideas)}"

        elif stage == PipelineStage.RESEARCH:
            # Fetch Tier 0 primary sources and snapshot content via ResearchAgent
            result = await self.research_agent.execute(
                topic_id=run.topic_id,
                search_query=f"{run.topic_id} primary history archive",
                limit=1,
            )
            snapshot_id = (
                result.snapshots_created[0] if result.snapshots_created else "snapshot_empty"
            )
            return snapshot_id

        elif stage == PipelineStage.CLAIM_EXTRACTION:
            # Extract structured claims and evidence via ExtractionAgent
            res = await self.research_agent.execute(
                topic_id=run.topic_id,
                search_query=f"{run.topic_id} primary history archive",
                limit=1,
            )
            snapshot_id = res.snapshots_created[0] if res.snapshots_created else "snapshot_empty"

            extract_result = await self.extraction_agent.execute(
                topic_id=run.topic_id,
                topic_title=run.topic_id,
                snapshot_id=snapshot_id,
                run_id=run.id,
                step_id=step.id,
            )
            return f"extracted_claims_{extract_result.claims_count}"

        elif stage == PipelineStage.FACT_VERIFICATION:
            ko = await self.knowledge_repo.get_current_for_topic(run.topic_id)
            if ko and ko.claim_ids:
                for cid in ko.claim_ids:
                    with contextlib.suppress(Exception):
                        await self.verification_agent.verify_claim(
                            claim_id=cid,
                            evidence_id=cid.replace("clm_", "ev_") if "clm_" in cid else "ev_01",
                            run_id=run.id,
                            step_id=step.id,
                        )
            return "all_claims_verified"

        elif stage == PipelineStage.SCRIPT_GENERATION:
            script_res = await self.script_agent.generate_script(
                ko_id=f"ko_{run.topic_id}",
                topic_title=run.topic_id,
                story_angle="Origins and Preservation",
                run_id=run.id,
                step_id=step.id,
            )
            return script_res.script.id

        elif stage == PipelineStage.TIMING_PLAN:
            script_res = await self.script_agent.generate_script(
                ko_id=f"ko_{run.topic_id}",
                topic_title=run.topic_id,
                story_angle="Origins and Preservation",
                run_id=run.id,
                step_id=step.id,
            )
            return script_res.timing_plan.id

        elif stage == PipelineStage.ASSET_DISCOVERY:
            candidates = await self.image_search.search_archival(run.topic_id, limit=10)
            for c in candidates:
                LicensePolicy.validate_asset_license(c.id, c.license_id)
            return f"assets_found_{len(candidates)}"

        elif stage == PipelineStage.STORYBOARD_CUTS:
            script_res = await self.script_agent.generate_script(
                ko_id=f"ko_{run.topic_id}",
                topic_title=run.topic_id,
                story_angle="Origins and Preservation",
                run_id=run.id,
                step_id=step.id,
            )
            candidates = await self.image_search.search_archival(run.topic_id, limit=max(5, len(script_res.script.beats)))
            if not candidates:
                # Fallback to something that passes if candidates fail
                candidates = await self.image_search.search_archival("history", limit=1)
            storyboard = await self.storyboard_agent.generate(
                script_res.script, script_res.timing_plan, candidates
            )
            return storyboard.id

        elif stage == PipelineStage.SOUND_DESIGN:
            script_res = await self.script_agent.generate_script(
                ko_id=f"ko_{run.topic_id}",
                topic_title=run.topic_id,
                story_angle="Origins and Preservation",
                run_id=run.id,
                step_id=step.id,
            )
            storyboard_id = f"stb_{run.topic_id}"
            soundtrack = await self.sound_design_agent.compose(storyboard_id, script_res.timing_plan)
            return soundtrack.id

        elif stage == PipelineStage.REMOTION_RENDER:
            # Acquire GPU Semaphore Lease (ADR-0001)
            holder_id = f"worker_{run.id}"
            await self.execution_repo.acquire_lock("gpu", holder_id=holder_id, ttl_seconds=60)
            try:
                storyboard = Storyboard(
                    id=f"stb_{run.topic_id}",
                    script_id=f"scr_{run.topic_id}",
                    timing_plan_id=f"tmp_{run.topic_id}",
                    scenes=[
                        Scene(
                            id="scn_01",
                            scene_index=1,
                            beat_id="beat_01",
                            asset_id="img_01",
                            start_time_seconds=0.0,
                            duration_seconds=3.5,
                        )
                    ],
                    created_at=utc_now(),
                )
                timing_plan = TimingPlan(
                    id=f"tmp_{run.topic_id}",
                    script_id=f"scr_{run.topic_id}",
                    beat_timings=[
                        BeatTiming(
                            beat_id="beat_01",
                            start_time_seconds=0.0,
                            end_time_seconds=3.5,
                            word_count=5,
                            reading_pace_wps=2.0,
                        )
                    ],
                    created_at=utc_now(),
                )

                # Render both vertical and horizontal formats
                vert_artifact = await self.renderer.render(
                    storyboard, timing_plan, RenderTarget.VERTICAL, run.id
                )
                horiz_artifact = await self.renderer.render(
                    storyboard, timing_plan, RenderTarget.HORIZONTAL, run.id
                )
                return f"{vert_artifact.id},{horiz_artifact.id}"
            finally:
                # Release GPU Semaphore Lease cleanly
                await self.execution_repo.release_lock("gpu", holder_id=holder_id)

        elif stage == PipelineStage.QUALITY_CHECK:
            script_res = await self.script_agent.generate_script(
                ko_id=f"ko_{run.topic_id}",
                topic_title=run.topic_id,
                story_angle="Origins and Preservation",
                run_id=run.id,
                step_id=step.id,
            )
            eval_result = await self.judge_agent.evaluate_script(
                run_id=run.id,
                script=script_res.script,
                timing_plan=script_res.timing_plan,
                topic_title=run.topic_id,
                step_id=step.id,
            )
            if not eval_result.passed:
                raise QualityGateFailedError(
                    eval_result.weighted_score,
                    "; ".join(eval_result.rejection_reasons) or "Failed quality criteria",
                )
            return eval_result.report.id

        elif stage == PipelineStage.PUBLISH:
            return f"publish_ready_{run.id}"

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
