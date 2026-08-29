"""Integration tests for non-negotiable architectural invariants (T-07).

These tests assert against database state after pipeline and agent execution to ensure
invariants are enforced by runtime checks, not decorative functions (Rule R10).

Each test is marked xfail(strict=True) naming its defect ID until resolved in Stage C/D.
"""

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
from atlas.adapters.persistence.repositories.publishing_repository import PublishingRepository
from atlas.adapters.persistence.repositories.source_repository import SourceRepository
from atlas.adapters.storage.local import LocalStorage
from atlas.application.agents.extraction import ExtractionAgent
from atlas.application.pipeline.runner import PipelineRunner
from atlas.application.ports.media import ImageCandidate
from atlas.application.usecases.approve_gate import ApproveGateUseCase
from atlas.application.usecases.create_run import CreateRunUseCase
from atlas.domain.common.enums import SourceTier
from atlas.domain.execution.models import RunStatus
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
from atlas.platform.errors import AiImageUnapprovedError
from atlas.platform.ids import generate_claim_id, generate_snapshot_id, generate_source_id
from atlas.platform.quota import QuotaManager
from pydantic import HttpUrl
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


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
@pytest.mark.xfail(
    strict=True,
    reason="Defect D-06: No check ensures claims have evidence links before shipping in KnowledgeObjectVersion",
)
async def test_no_claim_reaches_output_without_evidence(db_session: AsyncSession) -> None:
    """Every claim referenced by a shipped KnowledgeObjectVersion has >=1 row in claim_evidence (Invariant 1, D-06)."""
    know_repo = KnowledgeRepository(db_session)
    src_repo = SourceRepository(db_session)

    # Create an unlinked claim (0 evidence links)
    orphan_claim = Claim(
        id=generate_claim_id(),
        text="Chess was invented in ancient India.",
        assertion_type=AssertionType.FACT,
        status=ClaimStatus.UNSUPPORTED,
        confidence=0.9,
        created_at=utc_now(),
    )
    await src_repo.save_claim(orphan_claim)

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
    await know_repo.save_version(ko_version)

    # Query database to assert whether any claim in a released KO lacks evidence links
    res = await db_session.execute(
        text("""
        SELECT koc.claim_id
        FROM knowledge_object_claims koc
        LEFT JOIN claim_evidence ce ON koc.claim_id = ce.claim_id
        WHERE ce.evidence_id IS NULL
    """)
    )
    unlinked_claims = res.fetchall()

    # Invariant 1 enforcement: No claim in a Knowledge Object may have 0 evidence links
    assert len(unlinked_claims) == 0, (
        f"Defect D-06: Found claims in Knowledge Objects with 0 evidence links: {unlinked_claims}"
    )


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=True,
    reason="Defect D-04: Evidence quotes are not verified to be verbatim substrings of snapshot bytes",
)
async def test_every_evidence_quote_is_verbatim_in_its_snapshot(
    db_session: AsyncSession, tmp_path: Any
) -> None:
    """Evidence quote must be a verbatim substring of bytes stored under snapshots.content_hash (Invariant 1, D-04)."""
    storage = LocalStorage(root_dir=str(tmp_path))
    src_repo = SourceRepository(db_session)
    know_repo = KnowledgeRepository(db_session)
    exec_repo = ExecutionRepository(db_session)
    quota_mgr = QuotaManager(exec_repo)

    # 1. Store snapshot bytes representing a real primary source
    source_text = "Chaturanga is an ancient Indian strategy game developed during the Gupta Empire."
    source_bytes = source_text.encode("utf-8")
    content_hash = "a" * 64
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

    # 2. Configure FakeLlm to return a non-verbatim (hallucinated) quote
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
        run_id="run_inv_01",
        step_id="step_inv_01",
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
@pytest.mark.xfail(
    strict=True,
    reason="Defect D-02: ExtractionAgent sets status=ClaimStatus.VERIFIED at creation time",
)
async def test_claim_is_not_verified_at_extraction_time(
    db_session: AsyncSession, tmp_path: Any
) -> None:
    """After CLAIM_EXTRACTION and before FACT_VERIFICATION, no claim has status=verified (Invariant 2, D-02)."""
    storage = LocalStorage(root_dir=str(tmp_path))
    src_repo = SourceRepository(db_session)
    know_repo = KnowledgeRepository(db_session)
    exec_repo = ExecutionRepository(db_session)
    quota_mgr = QuotaManager(exec_repo)

    source_bytes = b"Primary archival text for extraction testing."
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
        content_hash="b" * 64,
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
        run_id="run_inv_02",
        step_id="step_inv_02",
    )

    # Check database state after extraction
    res = await db_session.execute(text("SELECT id, status FROM claims"))
    claims = res.fetchall()
    assert len(claims) > 0, "Extraction produced no claims"

    for claim_id, status in claims:
        assert status != ClaimStatus.VERIFIED.value, (
            f"Defect D-02: Claim '{claim_id}' was marked VERIFIED at extraction time before verification"
        )


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=True,
    reason="Defect D-01: RoutingPolicy defaults use_fakes=True and records provider=fake in production",
)
async def test_model_call_provenance_matches_the_adapter_that_ran(
    db_session: AsyncSession, tmp_path: Any
) -> None:
    """No model_calls row has provider=fake when running via production container (Invariant 7, D-01)."""
    storage = LocalStorage(root_dir=str(tmp_path))
    src_repo = SourceRepository(db_session)
    know_repo = KnowledgeRepository(db_session)
    exec_repo = ExecutionRepository(db_session)
    quota_mgr = QuotaManager(exec_repo)

    source_bytes = b"Archival text for testing model call provenance."
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
        content_hash="c" * 64,
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

    run_id = "run_prov_01"
    await agent.execute(
        topic_id="chess_origins",
        topic_title="Origin of Chess",
        snapshot_id=snapshot.id,
        run_id=run_id,
        step_id="step_prov_01",
    )

    # Invariant 7: Query model_calls table and ensure no production call records provider='fake'
    res = await db_session.execute(
        text("SELECT provider, model_id FROM model_calls WHERE run_id = :run_id"),
        {"run_id": run_id},
    )
    model_calls = res.fetchall()
    assert len(model_calls) > 0, "No model_calls recorded during extraction"

    for provider, model_id in model_calls:
        assert provider != "fake", (
            f"Defect D-01: model_calls recorded provider='fake' (model_id='{model_id}') in database"
        )


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=True,
    reason="Defect D-05: LicensePolicy.validate_ai_image_approval has zero production callers",
)
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

    await _seed_prerequisites(focus_repo, src_repo, pub_repo, "origin_of_ai", "origins")

    # Image candidate representing an AI-generated asset
    ai_candidate = ImageCandidate(
        id="img_ai_synth_01",
        url="https://example.com/ai_image.png",
        title="AI generated synthesis",
        author="Stable Diffusion",
        license_id="cc0",
        source_archive="local_sd",
    )
    image_search = FakeImageSearch(candidates=[ai_candidate])

    runner = PipelineRunner(
        execution_repo=exec_repo,
        knowledge_repo=know_repo,
        focus_repo=focus_repo,
        source_repo=src_repo,
        publishing_repo=pub_repo,
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

    create_run_uc = CreateRunUseCase(exec_repo, focus_repo, FakeQueueBroker())
    approve_gate_uc = ApproveGateUseCase(exec_repo, FakeQueueBroker())

    run = await create_run_uc.execute(
        topic_id="origin_of_ai", channel_id="origins", actor_id="operator_alice"
    )

    # Approve up to storyboard cuts
    run = await runner.run_pipeline(run.id)  # TOPIC_APPROVAL
    pending = await exec_repo.list_pending_gates()
    await approve_gate_uc.execute(gate_id=pending[0].id, actor_id="operator_alice")

    run = await runner.run_pipeline(run.id)  # KO_APPROVAL
    pending = await exec_repo.list_pending_gates()
    await approve_gate_uc.execute(gate_id=pending[0].id, actor_id="operator_alice")

    run = await runner.run_pipeline(run.id)  # SCRIPT_APPROVAL
    pending = await exec_repo.list_pending_gates()
    await approve_gate_uc.execute(gate_id=pending[0].id, actor_id="operator_alice")

    # When runner attempts to use unapproved AI image, it must raise AiImageUnapprovedError
    with pytest.raises(AiImageUnapprovedError):
        await runner.run_pipeline(run.id)


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=True,
    reason="Defects R-01, R-02: Remotion renderer discards upstream storyboard and script",
)
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

    await _seed_prerequisites(focus_repo, src_repo, pub_repo, "origin_of_geometry", "origins")

    renderer = FakeRenderer(storage)
    runner = PipelineRunner(
        execution_repo=exec_repo,
        knowledge_repo=know_repo,
        focus_repo=focus_repo,
        source_repo=src_repo,
        publishing_repo=pub_repo,
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

    create_run_uc = CreateRunUseCase(exec_repo, focus_repo, FakeQueueBroker())
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

    # Check that renderer received the storyboard generated upstream with real scene beats
    # In current defective code (R-01), REMOTION_RENDER creates a literal storyboard with 1 scene and 0 cues
    assert renderer.last_storyboard is not None, (
        "Defect R-01: Renderer did not receive any Storyboard"
    )
    assert len(renderer.last_storyboard.scenes) >= 12, (
        f"Defect R-01: Storyboard only has {len(renderer.last_storyboard.scenes)} scenes (expected >= 12 from approved script)"
    )
