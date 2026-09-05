"""Integration tests for non-negotiable architectural invariants (T-07).

These tests assert against database state after pipeline and agent execution to ensure
invariants are enforced by runtime checks, not decorative functions (Rule R10).

As of 2026-08-31 every test here asserts a behaviour that holds; none is marked xfail.
"""

import hashlib
import json
from typing import Any

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
from atlas.adapters.persistence.tables import GateTable
from atlas.adapters.storage.local import LocalStorage
from atlas.application.agents.extraction import ExtractionAgent
from atlas.application.pipeline.runner import PipelineRunner
from atlas.application.ports.llm import Extracted, LlmCapabilities, LlmRequest
from atlas.application.ports.media import ImageCandidate
from atlas.application.usecases.approve_gate import ApproveGateUseCase
from atlas.application.usecases.create_run import CreateRunUseCase
from atlas.domain.common.enums import SourceTier
from atlas.domain.execution.models import GateStatus, PipelineStage, RunStatus, Step, StepStatus
from atlas.domain.focus.models import Domain, ResearchProfile
from atlas.domain.knowledge.models import (
    AssertionType,
    Claim,
    ClaimStatus,
    KnowledgeObjectStatus,
    KnowledgeObjectVersion,
    Snapshot,
    Source,
    Topic,
    TopicStatus,
)
from atlas.domain.knowledge.payload import KnowledgePayloadV1
from atlas.domain.publishing.models import Channel
from atlas.platform.clock import utc_now
from atlas.platform.errors import (
    AiImageUnapprovedError,
    StepExecutionError,
    TraceabilityConstraintError,
)
from atlas.platform.ids import (
    generate_claim_id,
    generate_id,
    generate_snapshot_id,
    generate_source_id,
)
from atlas.platform.quota import QuotaManager
from pydantic import BaseModel, HttpUrl
from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import AsyncSession


class UnlinkedExtractionLlm:
    """Extraction double returning one claim and one quote but no link between them.

    Deliberately synthetic strings only (rule R4): this fixture must never read
    like a real historical fact.
    """

    @property
    def capabilities(self) -> LlmCapabilities:
        return LlmCapabilities(tier=2)

    async def extract(self, _request: LlmRequest, schema: type[BaseModel]) -> Extracted:
        payload = {
            "claims": [{"text": "Orphan claim.", "assertion_type": "fact", "confidence": 0.9}],
            "evidence": [{"quote": "PLACEHOLDER_DOCUMENT_C", "locator": "page 1"}],
            "links": [],
        }
        return Extracted(
            data=schema(**payload),
            input_tokens=10,
            output_tokens=10,
            latency_ms=10,
            raw_response=json.dumps(payload),
            model_id="fake-model",
            provider="fake",
        )


async def _seed_prerequisites(
    focus_repo: FocusRepository,
    src_repo: SourceRepository,
    pub_repo: PublishingRepository,
    topic_id: str,
    channel_id: str = "origins",
) -> None:
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
async def test_no_claim_reaches_output_without_evidence(db_session: AsyncSession) -> None:
    """Every claim referenced by a shipped KnowledgeObjectVersion has >=1 row in claim_evidence (Invariant 1, D-06)."""
    know_repo = KnowledgeRepository(db_session)
    src_repo = SourceRepository(db_session)
    focus_repo = FocusRepository(db_session)
    pub_repo = PublishingRepository(db_session)

    await _seed_prerequisites(focus_repo, src_repo, pub_repo, "chess_origins")

    # Create an unlinked claim (0 evidence links)
    orphan_claim = Claim(
        id=generate_claim_id(),
        text="Chess was invented in ancient India.",
        assertion_type=AssertionType.FACT,
        status=ClaimStatus.UNSUPPORTED,
        confidence=0.9,
        created_at=utc_now(),
    )
    await src_repo.save_claim(orphan_claim, actor_id="test.seed", reason="Fixture seed")

    # Create a KnowledgeObjectVersion containing this unlinked claim
    ko_version = KnowledgeObjectVersion(
        ko_id="ko_chess_origins",
        version=1,
        topic_id="chess_origins",
        status=KnowledgeObjectStatus.DRAFT,
        actor_id="operator_alice",
        reason="Test KO creation",
        claim_ids=[orphan_claim.id],
        payload=KnowledgePayloadV1(
            summary="Origin of chess summary",
            angles=["Origins"],
            keywords=["chess"],
        ),
        created_at=utc_now(),
    )
    # Invariant 1 enforcement: the save is refused outright. Asserting the absence of the row
    # instead would pass just as well if the claim were silently dropped (defect SC-04).
    with pytest.raises(TraceabilityConstraintError) as refusal:
        await know_repo.save_version(ko_version)
    assert orphan_claim.id in str(refusal.value), (
        f"The refusal must name the offending claim, got: {refusal.value}"
    )

    # Nothing from the refused version reached the database
    res = await db_session.execute(
        text("""
        SELECT koc.claim_id
        FROM knowledge_object_claims koc
        LEFT JOIN claim_evidence ce ON koc.claim_id = ce.claim_id
        WHERE ce.evidence_id IS NULL
    """)
    )
    unlinked_claims = res.fetchall()
    assert len(unlinked_claims) == 0, (
        f"Defect D-06: Found claims in Knowledge Objects with 0 evidence links: {unlinked_claims}"
    )

    versions = await db_session.execute(
        text("SELECT ko_id FROM knowledge_object_versions WHERE ko_id = :ko_id"),
        {"ko_id": ko_version.ko_id},
    )
    assert versions.fetchall() == [], (
        "The refused Knowledge Object version must not be persisted at all"
    )


@pytest.mark.asyncio
async def test_every_evidence_quote_is_verbatim_in_its_snapshot(
    db_session: AsyncSession, tmp_path: Any
) -> None:
    """Evidence quote must be a verbatim substring of bytes stored under snapshots.content_hash (Invariant 1, D-04)."""
    storage = LocalStorage(root_dir=str(tmp_path))
    src_repo = SourceRepository(db_session)
    know_repo = KnowledgeRepository(db_session)
    exec_repo = ExecutionRepository(db_session)
    focus_repo = FocusRepository(db_session)
    pub_repo = PublishingRepository(db_session)
    quota_mgr = QuotaManager(exec_repo)

    await _seed_prerequisites(focus_repo, src_repo, pub_repo, "chess_origins")
    create_run_uc = CreateRunUseCase(exec_repo, focus_repo, FakeQueueBroker(), src_repo, pub_repo)
    run = await create_run_uc.execute(topic_id="chess_origins", channel_id="origins")
    step = Step(
        id="step_inv_01",
        run_id=run.id,
        step_name="claim_extraction",
        step_index=4,
        input_hash="hash_01",
        status=StepStatus.RUNNING,
        started_at=utc_now(),
    )
    await exec_repo.create_step(step)

    # 1. Store snapshot bytes representing a real primary source
    source_text = (
        "Lorem source about SUBJECT_A. "
        "SUBJECT_A was recorded by SOURCE_B. "
        "SUBJECT_A is described in PLACEHOLDER_DOCUMENT_C."
    )
    source_bytes = source_text.encode("utf-8")
    content_hash = hashlib.sha256(source_bytes).hexdigest()
    storage_key = await storage.put(source_bytes, "text/plain")

    source = Source(
        id=generate_source_id(),
        title="Primary Source on Chess",
        url=HttpUrl("https://archive.org/details/chess_history"),
        source_tier=SourceTier.PRIMARY,
        created_at=utc_now(),
    )
    await src_repo.save_source(source)

    snapshot = Snapshot(
        id=generate_snapshot_id(),
        source_id=source.id,
        content_hash=content_hash,
        storage_key=storage_key,
        byte_size=len(source_bytes),
        mime_type="text/plain",
        retrieved_at=utc_now(),
    )
    await src_repo.save_snapshot(snapshot)

    llm = FakeLlm()
    agent = ExtractionAgent(
        llm=llm,
        storage=storage,
        source_repo=src_repo,
        knowledge_repo=know_repo,
        quota_mgr=quota_mgr,
    )

    result = await agent.execute(
        topic_id="chess_origins",
        topic_title="Origin of Chess",
        snapshot_id=snapshot.id,
        run_id=run.id,
        step_id=step.id,
    )
    assert result.evidence_count > 0

    # 3. Retrieve stored evidence rows from database and verify verbatim substring matching
    res = await db_session.execute(text("SELECT quote, snapshot_id FROM evidence"))
    saved_evidence = res.fetchall()

    for quote, snap_id in saved_evidence:
        snap = await src_repo.get_snapshot(snap_id)
        assert snap is not None
        raw_bytes = await storage.get(snap.storage_key)
        decoded_text = raw_bytes.decode("utf-8")
        assert quote in decoded_text, (
            f"Defect D-04: Evidence quote '{quote}' is not a verbatim substring of snapshot text"
        )


@pytest.mark.asyncio
async def test_claim_is_not_verified_at_extraction_time(
    db_session: AsyncSession, tmp_path: Any
) -> None:
    """After CLAIM_EXTRACTION and before FACT_VERIFICATION, no claim has status=verified (Invariant 2, D-02)."""
    storage = LocalStorage(root_dir=str(tmp_path))
    src_repo = SourceRepository(db_session)
    know_repo = KnowledgeRepository(db_session)
    exec_repo = ExecutionRepository(db_session)
    focus_repo = FocusRepository(db_session)
    pub_repo = PublishingRepository(db_session)
    quota_mgr = QuotaManager(exec_repo)

    await _seed_prerequisites(focus_repo, src_repo, pub_repo, "chess_origins")
    create_run_uc = CreateRunUseCase(exec_repo, focus_repo, FakeQueueBroker(), src_repo, pub_repo)
    run = await create_run_uc.execute(topic_id="chess_origins", channel_id="origins")
    step = Step(
        id="step_inv_02",
        run_id=run.id,
        step_name="claim_extraction",
        step_index=4,
        input_hash="hash_01",
        status=StepStatus.RUNNING,
        started_at=utc_now(),
    )
    await exec_repo.create_step(step)

    # Must contain the fake extractor's quotes verbatim, or the evidence is dropped and the
    # Knowledge Object save is refused (Invariant 1, T-45).
    source_bytes = (
        b"Lorem source about SUBJECT_A. SUBJECT_A was recorded by SOURCE_B. "
        b"SUBJECT_A is described in PLACEHOLDER_DOCUMENT_C."
    )
    storage_key = await storage.put(source_bytes, "text/plain")

    source = Source(
        id=generate_source_id(),
        title="Extraction Source",
        url=HttpUrl("https://archive.org/details/test_source"),
        source_tier=SourceTier.PRIMARY,
        created_at=utc_now(),
    )
    await src_repo.save_source(source)

    snapshot = Snapshot(
        id=generate_snapshot_id(),
        source_id=source.id,
        content_hash=hashlib.sha256(source_bytes).hexdigest(),
        storage_key=storage_key,
        byte_size=len(source_bytes),
        mime_type="text/plain",
        retrieved_at=utc_now(),
    )
    await src_repo.save_snapshot(snapshot)

    agent = ExtractionAgent(
        llm=FakeLlm(),
        storage=storage,
        source_repo=src_repo,
        knowledge_repo=know_repo,
        quota_mgr=quota_mgr,
    )

    await agent.execute(
        topic_id="chess_origins",
        topic_title="Origin of Chess",
        snapshot_id=snapshot.id,
        run_id=run.id,
        step_id=step.id,
    )

    # Check database state after extraction
    res = await db_session.execute(
        text(
            "SELECT v.claim_id, v.status FROM claim_versions v "
            "WHERE v.version = (SELECT MAX(v2.version) FROM claim_versions v2 "
            "WHERE v2.claim_id = v.claim_id)"
        )
    )
    claims = res.fetchall()
    assert len(claims) > 0, "Extraction produced no claims"

    for claim_id, status in claims:
        assert status != ClaimStatus.VERIFIED.value, (
            f"Defect D-02: Claim '{claim_id}' was marked VERIFIED at extraction time before verification"
        )


@pytest.mark.asyncio
async def test_model_call_provenance_matches_the_adapter_that_ran(
    db_session: AsyncSession, tmp_path: Any
) -> None:
    """No model_calls row has provider=fake when running via production container (Invariant 7, D-01)."""
    storage = LocalStorage(root_dir=str(tmp_path))
    src_repo = SourceRepository(db_session)
    know_repo = KnowledgeRepository(db_session)
    exec_repo = ExecutionRepository(db_session)
    focus_repo = FocusRepository(db_session)
    pub_repo = PublishingRepository(db_session)
    quota_mgr = QuotaManager(exec_repo)

    await _seed_prerequisites(focus_repo, src_repo, pub_repo, "chess_origins")
    create_run_uc = CreateRunUseCase(exec_repo, focus_repo, FakeQueueBroker(), src_repo, pub_repo)
    run = await create_run_uc.execute(topic_id="chess_origins", channel_id="origins")
    step = Step(
        id="step_prov_01",
        run_id=run.id,
        step_name="claim_extraction",
        step_index=4,
        input_hash="hash_01",
        status=StepStatus.RUNNING,
        started_at=utc_now(),
    )
    await exec_repo.create_step(step)

    source_bytes = (
        b"Lorem source about SUBJECT_A. SUBJECT_A was recorded by SOURCE_B. "
        b"SUBJECT_A is described in PLACEHOLDER_DOCUMENT_C."
    )
    storage_key = await storage.put(source_bytes, "text/plain")

    source = Source(
        id=generate_source_id(),
        title="Provenance Source",
        url=HttpUrl("https://archive.org/details/provenance_source"),
        source_tier=SourceTier.PRIMARY,
        created_at=utc_now(),
    )
    await src_repo.save_source(source)

    snapshot = Snapshot(
        id=generate_snapshot_id(),
        source_id=source.id,
        content_hash=hashlib.sha256(source_bytes).hexdigest(),
        storage_key=storage_key,
        byte_size=len(source_bytes),
        mime_type="text/plain",
        retrieved_at=utc_now(),
    )
    await src_repo.save_snapshot(snapshot)

    agent = ExtractionAgent(
        llm=FakeLlm(),
        storage=storage,
        source_repo=src_repo,
        knowledge_repo=know_repo,
        quota_mgr=quota_mgr,
    )

    await agent.execute(
        topic_id="chess_origins",
        topic_title="Origin of Chess",
        snapshot_id=snapshot.id,
        run_id=run.id,
        step_id=step.id,
    )

    # Invariant 7: Query model_calls table and ensure no production call records provider='fake'
    res = await db_session.execute(
        text("SELECT provider, model_id FROM model_calls WHERE run_id = :run_id"),
        {"run_id": run.id},
    )
    model_calls = res.fetchall()
    assert len(model_calls) > 0, "No model_calls recorded during extraction"

    for provider, model_id in model_calls:
        assert provider == "fake", (
            f"Defect D-01: model_calls recorded provider='{provider}' instead of 'fake' adapter that actually ran"
        )
        assert model_id == "fake-model", (
            f"Defect D-01: model_calls recorded model_id='{model_id}' instead of 'fake-model' adapter that actually ran"
        )


@pytest.mark.asyncio
async def test_ai_generated_asset_cannot_be_used_without_approval(
    db_session: AsyncSession, tmp_path: Any
) -> None:
    """An asset with is_ai_generated=true and no approval row causes the run to fail (Invariant 9, D-05)."""
    storage = LocalStorage(root_dir=str(tmp_path))
    exec_repo = ExecutionRepository(db_session)
    know_repo = KnowledgeRepository(db_session)
    focus_repo = FocusRepository(db_session)
    src_repo = SourceRepository(db_session)
    pub_repo = PublishingRepository(db_session)
    prod_repo = ProductionRepository(db_session)

    await _seed_prerequisites(focus_repo, src_repo, pub_repo, "origin_of_ai_unapproved", "origins")

    # Image candidate representing an AI-generated asset
    ai_candidate = ImageCandidate(
        id="img_ai_synth_01",
        url="https://example.com/ai_image.png",
        title="AI generated synthesis",
        author="Stable Diffusion",
        license_id="cc0",
        source_archive="local_sd",
        is_ai_generated=True,
    )
    image_search = FakeImageSearch(candidates=[ai_candidate])

    runner = PipelineRunner(
        execution_repo=exec_repo,
        knowledge_repo=know_repo,
        focus_repo=focus_repo,
        source_repo=src_repo,
        publishing_repo=pub_repo,
        production_repo=prod_repo,
        storage=storage,
        llm=FakeLlm(),
        embedder=FakeEmbedder(),
        search=FakeSearch(),
        source_fetcher=FakeSourceFetcher(),
        image_search=image_search,
        image_gen=FakeImageGenerator(),
        sound_lib=FakeSoundLibrary(),
        renderer=FakeRenderer(storage),
        notifier=FakeNotifier(),
        publisher=FakePublisher(),
        quota_mgr=QuotaManager(exec_repo),
    )

    create_run_uc = CreateRunUseCase(exec_repo, focus_repo, FakeQueueBroker(), src_repo, pub_repo)
    approve_gate_uc = ApproveGateUseCase(exec_repo, FakeQueueBroker())

    run = await create_run_uc.execute(
        topic_id="origin_of_ai_unapproved", channel_id="origins", actor_id="operator_alice"
    )

    # Drive the run to the asset-selection gate, then simulate a bug that flips the
    # gate row to `approved` without any human ever deciding: no Approval row is
    # written. Invariant 9 asks for a human decision, so the render must still refuse.
    asset_gate_step_id = f"step_{run.id}_{PipelineStage.ASSET_SELECTION.value}"

    with pytest.raises(StepExecutionError) as exc_info:
        while True:
            run = await runner.run_pipeline(run.id)
            if run.status != RunStatus.SUSPENDED:
                break

            pending = await exec_repo.list_pending_gates()
            if not pending:
                break

            gate = pending[0]
            if gate.step_id == asset_gate_step_id:
                await db_session.execute(
                    update(GateTable)
                    .where(GateTable.id == gate.id)
                    .values(status="approved", resolved_at=utc_now())
                )
                await db_session.flush()
                await exec_repo.update_run_status(run.id, RunStatus.RUNNING)
            else:
                await approve_gate_uc.execute(gate_id=gate.id, actor_id="operator_alice")

    assert isinstance(exc_info.value.__cause__, AiImageUnapprovedError)
    assert "img_ai_synth_01" in str(exc_info.value)

    # The bypass really did leave the gate reading `approved`; only the missing
    # Approval row stopped the render. Without this the test could pass because
    # the gate was still pending.
    bypassed_gates = await exec_repo.list_gates_for_run(run.id)
    bypassed = next(g for g in bypassed_gates if g.step_id == asset_gate_step_id)
    assert bypassed.status == GateStatus.APPROVED
    approvals = await exec_repo.list_approvals_for_run(run.id)
    assert all(a.gate_id != bypassed.id for a in approvals)


@pytest.mark.asyncio
async def test_ai_generated_asset_is_usable_once_a_human_approves_the_gate(
    db_session: AsyncSession, tmp_path: Any
) -> None:
    """A recorded human approval lets an AI-generated asset through (Invariant 9, defect SC-03).

    The mirror of the test above: without it, an approval check that is hardwired
    to False passes the negative case while making approval impossible.
    """
    storage = LocalStorage(root_dir=str(tmp_path))
    exec_repo = ExecutionRepository(db_session)
    know_repo = KnowledgeRepository(db_session)
    focus_repo = FocusRepository(db_session)
    src_repo = SourceRepository(db_session)
    pub_repo = PublishingRepository(db_session)
    prod_repo = ProductionRepository(db_session)

    await _seed_prerequisites(focus_repo, src_repo, pub_repo, "origin_of_ai_approved", "origins")

    ai_candidate = ImageCandidate(
        id="img_ai_synth_02",
        url="https://example.com/ai_image_2.png",
        title="AI generated synthesis",
        author="Stable Diffusion",
        license_id="cc0",
        source_archive="local_sd",
        is_ai_generated=True,
    )
    runner = PipelineRunner(
        execution_repo=exec_repo,
        knowledge_repo=know_repo,
        focus_repo=focus_repo,
        source_repo=src_repo,
        publishing_repo=pub_repo,
        production_repo=prod_repo,
        storage=storage,
        llm=FakeLlm(),
        embedder=FakeEmbedder(),
        search=FakeSearch(),
        source_fetcher=FakeSourceFetcher(),
        image_search=FakeImageSearch(candidates=[ai_candidate]),
        image_gen=FakeImageGenerator(),
        sound_lib=FakeSoundLibrary(),
        renderer=FakeRenderer(storage),
        notifier=FakeNotifier(),
        publisher=FakePublisher(),
        quota_mgr=QuotaManager(exec_repo),
    )

    create_run_uc = CreateRunUseCase(exec_repo, focus_repo, FakeQueueBroker(), src_repo, pub_repo)
    approve_gate_uc = ApproveGateUseCase(exec_repo, FakeQueueBroker())
    run = await create_run_uc.execute(
        topic_id="origin_of_ai_approved", channel_id="origins", actor_id="operator_alice"
    )

    while True:
        run = await runner.run_pipeline(run.id)
        if run.status != RunStatus.SUSPENDED:
            break
        pending = await exec_repo.list_pending_gates()
        if not pending:
            break
        await approve_gate_uc.execute(gate_id=pending[0].id, actor_id="operator_alice")

    assert run.status == RunStatus.COMPLETED
    storyboard_step = next(
        s
        for s in await exec_repo.list_steps_for_run(run.id)
        if s.step_name == PipelineStage.STORYBOARD_CUTS.value
    )
    assert storyboard_step.status == StepStatus.SUCCEEDED
    storyboard = await prod_repo.get_storyboard(storyboard_step.output_artifact_ref or "")
    assert {scene.asset_id for scene in storyboard.scenes} == {"img_ai_synth_02"}


@pytest.mark.asyncio
async def test_rendered_artifact_derives_from_the_approved_script(
    db_session: AsyncSession, tmp_path: Any
) -> None:
    """The storyboard and timing plan given to the renderer must be the persisted ones for this run (R-01, R-02)."""
    storage = LocalStorage(root_dir=str(tmp_path))
    exec_repo = ExecutionRepository(db_session)
    know_repo = KnowledgeRepository(db_session)
    focus_repo = FocusRepository(db_session)
    src_repo = SourceRepository(db_session)
    pub_repo = PublishingRepository(db_session)
    prod_repo = ProductionRepository(db_session)

    await _seed_prerequisites(focus_repo, src_repo, pub_repo, "origin_of_geometry", "origins")

    renderer = FakeRenderer(storage)
    runner = PipelineRunner(
        execution_repo=exec_repo,
        knowledge_repo=know_repo,
        focus_repo=focus_repo,
        source_repo=src_repo,
        publishing_repo=pub_repo,
        production_repo=prod_repo,
        storage=storage,
        llm=FakeLlm(),
        embedder=FakeEmbedder(),
        search=FakeSearch(),
        source_fetcher=FakeSourceFetcher(),
        image_search=FakeImageSearch(),
        image_gen=FakeImageGenerator(),
        sound_lib=FakeSoundLibrary(),
        renderer=renderer,
        notifier=FakeNotifier(),
        publisher=FakePublisher(),
        quota_mgr=QuotaManager(exec_repo),
    )

    create_run_uc = CreateRunUseCase(exec_repo, focus_repo, FakeQueueBroker(), src_repo, pub_repo)
    approve_gate_uc = ApproveGateUseCase(exec_repo, FakeQueueBroker())

    run = await create_run_uc.execute(
        topic_id="origin_of_geometry", channel_id="origins", actor_id="operator_alice"
    )

    # Traverse all 6 gates
    for _ in range(6):
        run = await runner.run_pipeline(run.id)
        if run.status != RunStatus.SUSPENDED:
            break
        pending = await exec_repo.list_pending_gates()
        if not pending:
            break
        await approve_gate_uc.execute(gate_id=pending[0].id, actor_id="operator_alice")

    run = await runner.run_pipeline(run.id)
    assert run.status == RunStatus.COMPLETED

    # The renderer must receive the storyboard the pipeline persisted, not one
    # invented at render time (defects R-01, R-02).
    assert renderer.last_storyboard is not None
    storyboard_step = next(
        s
        for s in await exec_repo.list_steps_for_run(run.id)
        if s.step_name == PipelineStage.STORYBOARD_CUTS.value
    )
    persisted_storyboard = await prod_repo.get_storyboard(storyboard_step.output_artifact_ref or "")
    assert renderer.last_storyboard.id == persisted_storyboard.id
    assert len(renderer.last_storyboard.scenes) == len(persisted_storyboard.scenes)
    assert len(renderer.last_storyboard.scenes) >= 12

    # And the storyboard must derive from the script that stage 8 persisted and the
    # stage 9 gate approved, not from a script regenerated later.
    script_step = next(
        s
        for s in await exec_repo.list_steps_for_run(run.id)
        if s.step_name == PipelineStage.SCRIPT_GENERATION.value
    )
    assert persisted_storyboard.script_id == script_step.output_artifact_ref

    # Every render target is persisted, and each records the storyboard it came from.
    artifacts = await prod_repo.list_render_artifacts(run.id)
    assert {a.render_target for a in artifacts} == set(persisted_storyboard.render_targets)
    assert all(a.storyboard_id == persisted_storyboard.id for a in artifacts)


@pytest.mark.asyncio
async def test_claim_with_no_evidence_ends_unsupported_and_not_in_script(
    db_session: AsyncSession, tmp_path: Any
) -> None:
    """A claim with no evidence link becomes unsupported and never enters the Knowledge Object (T-15)."""
    storage = LocalStorage(root_dir=str(tmp_path))
    src_repo = SourceRepository(db_session)
    know_repo = KnowledgeRepository(db_session)
    exec_repo = ExecutionRepository(db_session)
    focus_repo = FocusRepository(db_session)
    pub_repo = PublishingRepository(db_session)
    quota_mgr = QuotaManager(exec_repo)

    await _seed_prerequisites(focus_repo, src_repo, pub_repo, "chess_origins")

    agent = ExtractionAgent(
        llm=UnlinkedExtractionLlm(),
        storage=storage,
        source_repo=src_repo,
        knowledge_repo=know_repo,
        quota_mgr=quota_mgr,
    )

    create_run_uc = CreateRunUseCase(exec_repo, focus_repo, FakeQueueBroker(), src_repo, pub_repo)
    run = await create_run_uc.execute(topic_id="chess_origins", channel_id="origins")

    step_id = generate_id("step")
    await exec_repo.create_step(
        Step(
            id=step_id,
            run_id=run.id,
            step_name=PipelineStage.CLAIM_EXTRACTION.value,
            step_index=4,
            input_hash="h",
            status=StepStatus.RUNNING,
            started_at=utc_now(),
        )
    )

    source = Source(
        id=generate_source_id(),
        title="Placeholder source",
        url=HttpUrl("https://example.invalid/placeholder"),
        source_tier=SourceTier.PRIMARY,
        created_at=utc_now(),
    )
    await src_repo.save_source(source)
    content = b"PLACEHOLDER_DOCUMENT_C"
    storage_key = await storage.put(content, mime_type="text/plain")
    snapshot = Snapshot(
        id=generate_snapshot_id(),
        source_id=source.id,
        content_hash=storage_key.split("/")[-1],
        storage_key=storage_key,
        byte_size=len(content),
        mime_type="text/plain",
        retrieved_at=utc_now(),
    )
    await src_repo.save_snapshot(snapshot)

    await agent.execute("chess_origins", "Chess", snapshot.id, run.id, step_id)

    # The claim exists, at its latest version, marked unsupported.
    res = await db_session.execute(
        text(
            "SELECT claim_id, status FROM claim_versions v WHERE v.text = 'Orphan claim.' "
            "AND v.version = (SELECT MAX(v2.version) FROM claim_versions v2 "
            "WHERE v2.claim_id = v.claim_id)"
        )
    )
    claim_row = res.fetchone()
    assert claim_row is not None
    assert claim_row[1] == ClaimStatus.UNSUPPORTED.value

    ko = await know_repo.get_current("ko_chess_origins")
    assert ko is not None
    assert claim_row[0] not in ko.claim_ids


@pytest.mark.asyncio
async def test_claim_state_changes_append_a_version_and_never_overwrite(
    db_session: AsyncSession,
) -> None:
    """A status change writes a new claim version; the previous one stays intact (Invariant 4)."""
    src_repo = SourceRepository(db_session)

    claim = Claim(
        id=generate_claim_id(),
        text="Placeholder assertion under test.",
        assertion_type=AssertionType.FACT,
        confidence=0.9,
        status=ClaimStatus.UNVERIFIED,
        created_at=utc_now(),
    )
    first = await src_repo.save_claim(
        claim, actor_id="agent.extraction", reason="Extracted from snapshot"
    )
    assert first.version == 1

    second = await src_repo.save_claim(
        claim.model_copy(update={"status": ClaimStatus.VERIFIED}),
        actor_id="agent.verification",
        reason="Supported by evidence quote",
    )
    assert second.version == 2

    history = await src_repo.get_claim_history(claim.id)
    assert [c.version for c in history] == [1, 2]
    assert history[0].status == ClaimStatus.UNVERIFIED
    assert history[1].status == ClaimStatus.VERIFIED

    current = await src_repo.get_claim(claim.id)
    assert current is not None
    assert current.status == ClaimStatus.VERIFIED
    assert current.version == 2

    rows = await db_session.execute(
        text(
            "SELECT version, actor_id, reason FROM claim_versions "
            "WHERE claim_id = :cid ORDER BY version"
        ),
        {"cid": claim.id},
    )
    recorded = rows.fetchall()
    assert [r[1] for r in recorded] == ["agent.extraction", "agent.verification"]
    assert all(r[2] for r in recorded), "Every claim version must record why it was written"
