"""End-to-End Pipeline Execution, State Machine, Gates, and GPU Lease Integration Tests.

Tests the full 17-stage state machine against PostgreSQL test database.
"""

import pytest
from atlas.adapters.fakes.providers import (
    FakeEmbedder,
    FakeImageGenerator,
    FakeImageSearch,
    FakeLlm,
    FakeNotifier,
    FakePublisher,
    FakeQueueBroker,
    FakeRenderer,
    FakeSearch,
    FakeSoundLibrary,
    FakeSourceFetcher,
)
from atlas.adapters.persistence.repositories.execution_repository import ExecutionRepository
from atlas.adapters.persistence.repositories.focus_repository import FocusRepository
from atlas.adapters.persistence.repositories.knowledge_repository import KnowledgeRepository
from atlas.adapters.persistence.repositories.production_repository import ProductionRepository
from atlas.adapters.persistence.repositories.publishing_repository import PublishingRepository
from atlas.adapters.persistence.repositories.source_repository import SourceRepository
from atlas.adapters.storage.local import LocalStorage
from atlas.application.pipeline.runner import PipelineRunner
from atlas.application.usecases.approve_gate import ApproveGateUseCase
from atlas.application.usecases.create_run import CreateRunUseCase
from atlas.application.usecases.reject_gate import RejectGateUseCase
from atlas.domain.execution.models import (
    ApprovalDecision,
    GateStatus,
    PipelineStage,
    RejectionAction,
    RejectionFeedback,
    RunStatus,
    StepStatus,
)
from atlas.domain.focus.models import Domain, ResearchProfile
from atlas.domain.knowledge.models import ClaimStatus, Topic, TopicStatus
from atlas.domain.media.models import RenderTarget
from atlas.domain.publishing.models import Channel
from atlas.platform.clock import utc_now
from atlas.platform.errors import GateAlreadyResolvedError, ResourceLockHeldError
from atlas.platform.quota import QuotaManager
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def test_storage(tmp_path: str) -> LocalStorage:
    return LocalStorage(root_dir=str(tmp_path))


async def _seed_topic_and_channel(
    focus_repo: FocusRepository,
    src_repo: SourceRepository,
    pub_repo: PublishingRepository,
    topic_id: str,
    channel_id: str = "origins",
) -> None:
    """Seed prerequisite foreign-key rows for Domain, Topic, and Channel."""
    domain = Domain(
        id="dom_science",
        name="Science & History",
        description="Historical and scientific research domain",
        research_profile=ResearchProfile(
            preferred_apis=["openalex", "smithsonian"],
            source_allowlist=["*.org", "*.edu"],
        ),
    )
    await focus_repo.save_domain(domain)

    topic = Topic(
        id=topic_id,
        title=f"History of {topic_id}",
        domain_id=domain.id,
        status=TopicStatus.PROPOSED,
        created_at=utc_now(),
    )
    await src_repo.save_topic(topic)

    channel = Channel(
        id=channel_id,
        name="Origins Channel",
        audience_timezone="UTC",
        style_profile={"visual_tone": "archival", "pacing": "contemplative"},
        created_at=utc_now(),
    )
    await pub_repo.save_channel(channel)


@pytest.mark.asyncio
async def test_full_18_stage_pipeline_traversal_with_human_gates(
    db_session: AsyncSession, test_storage: LocalStorage
) -> None:
    """Test full execution of all 17 pipeline stages with gate suspension, approval, and completion."""
    exec_repo = ExecutionRepository(db_session)
    know_repo = KnowledgeRepository(db_session)
    focus_repo = FocusRepository(db_session)
    src_repo = SourceRepository(db_session)
    pub_repo = PublishingRepository(db_session)
    prod_repo = ProductionRepository(db_session)

    queue_broker = FakeQueueBroker()
    quota_mgr = QuotaManager(exec_repo)
    renderer = FakeRenderer(test_storage)
    publisher = FakePublisher()

    runner = PipelineRunner(
        execution_repo=exec_repo,
        knowledge_repo=know_repo,
        focus_repo=focus_repo,
        source_repo=src_repo,
        publishing_repo=pub_repo,
        production_repo=prod_repo,
        storage=test_storage,
        llm=FakeLlm(),
        embedder=FakeEmbedder(),
        search=FakeSearch(),
        source_fetcher=FakeSourceFetcher(),
        image_search=FakeImageSearch(),
        image_gen=FakeImageGenerator(),
        sound_lib=FakeSoundLibrary(),
        renderer=renderer,
        notifier=FakeNotifier(),
        publisher=publisher,
        quota_mgr=quota_mgr,
    )

    create_run_uc = CreateRunUseCase(exec_repo, focus_repo, queue_broker)
    approve_gate_uc = ApproveGateUseCase(exec_repo, queue_broker)

    # 0. Seed foreign keys
    await _seed_topic_and_channel(
        focus_repo, src_repo, pub_repo, "origin_of_mathematics", "origins"
    )

    # 1. Create a new Run
    run = await create_run_uc.execute(
        topic_id="origin_of_mathematics", channel_id="origins", actor_id="operator_alice"
    )
    assert run.status == RunStatus.PENDING

    # 2. Run Pipeline -> Suspends at Gate 1: TOPIC_APPROVAL
    run = await runner.run_pipeline(run.id)
    assert run.status == RunStatus.SUSPENDED

    pending_gates = await exec_repo.list_pending_gates()
    assert len(pending_gates) == 1
    topic_gate = pending_gates[0]
    assert topic_gate.run_id == run.id

    # Approve Gate 1 (Topic)
    updated_gate, approval = await approve_gate_uc.execute(
        gate_id=topic_gate.id, actor_id="operator_alice"
    )
    assert updated_gate.status == GateStatus.APPROVED
    assert approval.decision == ApprovalDecision.APPROVED

    # 3. Resume Pipeline -> Executes Research, Extraction, Verification -> Suspends at Gate 2: KO_APPROVAL
    run = await runner.run_pipeline(run.id)
    assert run.status == RunStatus.SUSPENDED

    pending_gates = await exec_repo.list_pending_gates()
    assert len(pending_gates) == 1
    ko_gate = pending_gates[0]

    # Approve Gate 2 (Knowledge Object)
    updated_gate, approval = await approve_gate_uc.execute(
        gate_id=ko_gate.id, actor_id="operator_alice"
    )
    assert updated_gate.status == GateStatus.APPROVED

    # 4. Resume Pipeline -> Suspends at Gate 3: STORY_ANGLE (Hybrid Gate)
    run = await runner.run_pipeline(run.id)
    assert run.status == RunStatus.SUSPENDED

    pending_gates = await exec_repo.list_pending_gates()
    assert len(pending_gates) == 1
    angle_gate = pending_gates[0]

    # Approve Gate 3 (Story Angle)
    updated_gate, approval = await approve_gate_uc.execute(
        gate_id=angle_gate.id, actor_id="operator_alice"
    )
    assert updated_gate.status == GateStatus.APPROVED

    # 5. Resume Pipeline -> Executes Script Gen -> Suspends at Gate 4: SCRIPT_APPROVAL
    run = await runner.run_pipeline(run.id)
    assert run.status == RunStatus.SUSPENDED

    pending_gates = await exec_repo.list_pending_gates()
    assert len(pending_gates) == 1
    script_gate = pending_gates[0]

    # Approve Gate 4 (Script)
    updated_gate, approval = await approve_gate_uc.execute(
        gate_id=script_gate.id, actor_id="operator_alice"
    )
    assert updated_gate.status == GateStatus.APPROVED

    # 6. Resume Pipeline -> Executes Timing Plan, Asset Discovery -> Suspends at Gate 5: ASSET_SELECTION_APPROVAL
    run = await runner.run_pipeline(run.id)
    assert run.status == RunStatus.SUSPENDED

    pending_gates = await exec_repo.list_pending_gates()
    assert len(pending_gates) == 1
    asset_gate = pending_gates[0]

    # Approve Gate 5 (Assets)
    updated_gate, approval = await approve_gate_uc.execute(
        gate_id=asset_gate.id, actor_id="operator_alice"
    )
    assert updated_gate.status == GateStatus.APPROVED

    # 7. Resume Pipeline -> Executes Cuts, Sound, Remotion Render (with GPU lease), Quality Check -> Suspends at Gate 6: FINAL_RENDER_APPROVAL
    run = await runner.run_pipeline(run.id)
    assert run.status == RunStatus.SUSPENDED

    pending_gates = await exec_repo.list_pending_gates()
    assert len(pending_gates) == 1
    final_gate = pending_gates[0]

    # Approve Gate 5 (Final Render)
    updated_gate, approval = await approve_gate_uc.execute(
        gate_id=final_gate.id, actor_id="operator_alice"
    )
    assert updated_gate.status == GateStatus.APPROVED

    # 7. Resume Pipeline -> Publishes and completes!
    run = await runner.run_pipeline(run.id)
    assert run.status == RunStatus.COMPLETED
    assert run.completed_at is not None

    # Verify all steps completed
    steps = await exec_repo.list_steps_for_run(run.id)
    assert len(steps) == 18
    for s in steps:
        assert s.status == StepStatus.SUCCEEDED

    # Rule R6: reaching `completed` proves nothing. Inspect what the run actually wrote.
    steps_by_name = {s.step_name: s for s in steps}

    # Every claim in the Knowledge Object is traceable to evidence with a source.
    ko = await know_repo.get_current_for_topic("origin_of_mathematics")
    assert ko is not None
    assert ko.claim_ids
    for claim_id in ko.claim_ids:
        chain = await know_repo.get_traceability_chain(claim_id)
        assert chain.evidence_with_sources, f"Claim {claim_id} entered the KO with no evidence"
        assert chain.claim.status == ClaimStatus.VERIFIED

    # The script is persisted once, and every beat cites claims from that KO.
    script_id = steps_by_name[PipelineStage.SCRIPT_GENERATION.value].output_artifact_ref
    assert script_id is not None
    script = await prod_repo.get_script(script_id)
    assert script.beats
    for beat in script.beats:
        assert beat.claim_ids
        assert set(beat.claim_ids) <= set(ko.claim_ids)

    # Downstream stages reused that script rather than generating their own.
    timing_plan = await prod_repo.get_timing_plan_for_script(script.id)
    assert steps_by_name[PipelineStage.TIMING_PLAN.value].output_artifact_ref == timing_plan.id
    storyboard_id = steps_by_name[PipelineStage.STORYBOARD_CUTS.value].output_artifact_ref
    assert storyboard_id is not None
    storyboard = await prod_repo.get_storyboard(storyboard_id)
    assert storyboard.script_id == script.id
    assert storyboard.timing_plan_id == timing_plan.id
    assert len(storyboard.scenes) == len(script.beats)

    # Exactly one script generation call was metered, not one per downstream stage.
    script_calls = await db_session.execute(
        text("SELECT COUNT(*) FROM model_calls WHERE prompt_version = 'script_generation_v1'")
    )
    assert script_calls.scalar_one() == 1

    # Render artifacts exist for both targets, with captions that carry real cues.
    artifacts = await prod_repo.list_render_artifacts(run.id)
    assert {a.render_target for a in artifacts} == {
        RenderTarget.VERTICAL,
        RenderTarget.HORIZONTAL,
    }
    for artifact in artifacts:
        assert artifact.storyboard_id == storyboard.id
        assert artifact.duration_seconds == timing_plan.total_duration_seconds
        captions = (await test_storage.get(artifact.captions_storage_key)).decode("utf-8")
        assert captions.startswith("WEBVTT")
        assert "-->" in captions

    # Publication actually ran, once per artifact.
    assert len(publisher.published_records) == len(artifacts)
    assert steps_by_name[PipelineStage.PUBLISH.value].output_artifact_ref

    # Provenance records the adapter that ran, not the one the container would use.
    providers = await db_session.execute(text("SELECT DISTINCT provider FROM model_calls"))
    assert {row[0] for row in providers} == {"fake"}


@pytest.mark.asyncio
async def test_gate_structured_rejection_with_rework(
    db_session: AsyncSession, test_storage: LocalStorage
) -> None:
    """Test structured rejection at a gate transitions Run to REWORKING and enforces feedback."""
    exec_repo = ExecutionRepository(db_session)
    know_repo = KnowledgeRepository(db_session)
    focus_repo = FocusRepository(db_session)
    src_repo = SourceRepository(db_session)
    pub_repo = PublishingRepository(db_session)
    prod_repo = ProductionRepository(db_session)

    queue_broker = FakeQueueBroker()
    quota_mgr = QuotaManager(exec_repo)
    renderer = FakeRenderer(test_storage)

    runner = PipelineRunner(
        execution_repo=exec_repo,
        knowledge_repo=know_repo,
        focus_repo=focus_repo,
        source_repo=src_repo,
        publishing_repo=pub_repo,
        production_repo=prod_repo,
        storage=test_storage,
        llm=FakeLlm(),
        embedder=FakeEmbedder(),
        search=FakeSearch(),
        source_fetcher=FakeSourceFetcher(),
        image_search=FakeImageSearch(),
        image_gen=FakeImageGenerator(),
        sound_lib=FakeSoundLibrary(),
        renderer=renderer,
        notifier=FakeNotifier(),
        quota_mgr=quota_mgr,
    )

    create_run_uc = CreateRunUseCase(exec_repo, focus_repo, queue_broker)
    reject_gate_uc = RejectGateUseCase(exec_repo, queue_broker)

    await _seed_topic_and_channel(focus_repo, src_repo, pub_repo, "origin_of_astronomy", "origins")

    # 1. Create and start Run -> suspends at Topic Gate
    run = await create_run_uc.execute(topic_id="origin_of_astronomy")
    run = await runner.run_pipeline(run.id)
    assert run.status == RunStatus.SUSPENDED

    pending_gates = await exec_repo.list_pending_gates()
    gate = pending_gates[0]

    # 2. Reject with structured feedback (SPEC §7)
    feedback = RejectionFeedback(
        target_ref="topic_origin_of_astronomy",
        rubric_dimension="hook_strength",
        reason="The framing lacks audience tension in the first 3 seconds.",
        action=RejectionAction.REGENERATE,
    )
    rejected_gate, approval = await reject_gate_uc.execute(
        gate_id=gate.id, feedback=feedback, actor_id="operator_bob"
    )

    assert rejected_gate.status == GateStatus.REJECTED
    assert approval.decision == ApprovalDecision.REJECTED
    assert approval.feedback is not None
    assert approval.feedback.reason == "The framing lacks audience tension in the first 3 seconds."

    # Verify run transitioned to REWORKING
    reworking_run = await exec_repo.get_run(run.id)
    assert reworking_run.status == RunStatus.REWORKING

    # Double resolution is blocked
    with pytest.raises(GateAlreadyResolvedError):
        await reject_gate_uc.execute(gate_id=gate.id, feedback=feedback, actor_id="operator_bob")


@pytest.mark.asyncio
async def test_gate_rejection_with_abandonment(
    db_session: AsyncSession, test_storage: LocalStorage
) -> None:
    """Test rejection with action=ABANDON transitions Run directly to ABANDONED."""
    exec_repo = ExecutionRepository(db_session)
    know_repo = KnowledgeRepository(db_session)
    focus_repo = FocusRepository(db_session)
    src_repo = SourceRepository(db_session)
    pub_repo = PublishingRepository(db_session)
    prod_repo = ProductionRepository(db_session)

    queue_broker = FakeQueueBroker()
    quota_mgr = QuotaManager(exec_repo)
    renderer = FakeRenderer(test_storage)

    runner = PipelineRunner(
        execution_repo=exec_repo,
        knowledge_repo=know_repo,
        focus_repo=focus_repo,
        source_repo=src_repo,
        publishing_repo=pub_repo,
        production_repo=prod_repo,
        storage=test_storage,
        llm=FakeLlm(),
        embedder=FakeEmbedder(),
        search=FakeSearch(),
        source_fetcher=FakeSourceFetcher(),
        image_search=FakeImageSearch(),
        image_gen=FakeImageGenerator(),
        sound_lib=FakeSoundLibrary(),
        renderer=renderer,
        notifier=FakeNotifier(),
        quota_mgr=quota_mgr,
    )

    create_run_uc = CreateRunUseCase(exec_repo, focus_repo, queue_broker)
    reject_gate_uc = RejectGateUseCase(exec_repo, queue_broker)

    await _seed_topic_and_channel(focus_repo, src_repo, pub_repo, "abandon_candidate", "origins")

    run = await create_run_uc.execute(topic_id="abandon_candidate")
    run = await runner.run_pipeline(run.id)

    pending_gates = await exec_repo.list_pending_gates()
    gate = pending_gates[0]

    feedback = RejectionFeedback(
        target_ref="topic_abandon_candidate",
        rubric_dimension="sourcing_integrity",
        reason="Subject has insufficient primary archival records.",
        action=RejectionAction.ABANDON,
    )
    await reject_gate_uc.execute(gate_id=gate.id, feedback=feedback, actor_id="operator_bob")

    abandoned_run = await exec_repo.get_run(run.id)
    assert abandoned_run.status == RunStatus.ABANDONED


@pytest.mark.asyncio
async def test_gpu_semaphore_concurrency(db_session: AsyncSession) -> None:
    """Test atomic GPU semaphore acquisition and conflict rejection (SPEC §11.3)."""
    exec_repo = ExecutionRepository(db_session)

    # 1. Acquire GPU lock
    lock = await exec_repo.acquire_lock("gpu", holder_id="task_render_1", ttl_seconds=60)
    assert lock.resource_name == "gpu"
    assert lock.holder_id == "task_render_1"

    # 2. Second concurrent task must be rejected
    with pytest.raises(ResourceLockHeldError):
        await exec_repo.acquire_lock("gpu", holder_id="task_render_2", ttl_seconds=60)

    # 3. Release lock
    await exec_repo.release_lock("gpu", holder_id="task_render_1")

    # 4. Now second task can acquire
    lock2 = await exec_repo.acquire_lock("gpu", holder_id="task_render_2", ttl_seconds=60)
    assert lock2.holder_id == "task_render_2"
