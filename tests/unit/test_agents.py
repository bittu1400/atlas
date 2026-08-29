"""Unit tests for Phase 5 Agents (ResearchAgent, ExtractionAgent)."""

from typing import Any

import pytest
from atlas.adapters.fakes.providers import FakeLlm, FakeSearch, FakeSourceFetcher
from atlas.adapters.storage.local import LocalStorage
from atlas.application.agents.extraction import ExtractionAgent
from atlas.application.agents.judge import JudgeAgent
from atlas.application.agents.research import ResearchAgent
from atlas.application.agents.script import ScriptAgent
from atlas.application.agents.verification import VerificationAgent
from atlas.application.ports.repositories import (
    KnowledgeRepositoryPort,
    SourceRepositoryPort,
)
from atlas.domain.knowledge.models import (
    Claim,
    ClaimEvidenceLink,
    ClaimStatus,
    ClaimUsage,
    Evidence,
    KnowledgeObjectVersion,
    Snapshot,
    Source,
    Topic,
    TraceabilityChain,
)
from atlas.platform.clock import utc_now
from atlas.platform.quota import QuotaManager


class InMemorySourceRepository(SourceRepositoryPort):
    """In-memory source repository for hermetic unit testing."""

    def __init__(self) -> None:
        self.sources: dict[str, Source] = {}
        self.snapshots: dict[str, Snapshot] = {}
        self.evidence: dict[str, Evidence] = {}
        self.claims: dict[str, Claim] = {}
        self.links: list[ClaimEvidenceLink] = []

    async def save_topic(self, topic: Topic) -> Topic:
        return topic

    async def get_topic(self, _topic_id: str) -> Topic | None:
        return None

    async def save_source(self, source: Source) -> Source:
        self.sources[source.id] = source
        return source

    async def get_source(self, source_id: str) -> Source:
        return self.sources[source_id]

    async def save_snapshot(self, snapshot: Snapshot) -> Snapshot:
        self.snapshots[snapshot.id] = snapshot
        return snapshot

    async def get_snapshot(self, snapshot_id: str) -> Snapshot:
        return self.snapshots[snapshot_id]

    async def find_snapshot_by_hash(self, source_id: str, content_hash: str) -> Snapshot | None:
        for s in self.snapshots.values():
            if s.source_id == source_id and s.content_hash == content_hash:
                return s
        return None

    async def save_evidence(self, evidence: Evidence) -> Evidence:
        self.evidence[evidence.id] = evidence
        return evidence

    async def get_evidence(self, evidence_id: str) -> Evidence | None:
        return self.evidence.get(evidence_id)

    async def save_claim(self, claim: Claim) -> Claim:
        self.claims[claim.id] = claim
        return claim

    async def get_claim(self, claim_id: str) -> Claim | None:
        return self.claims.get(claim_id)

    async def link_claim_evidence(self, link: ClaimEvidenceLink) -> None:
        self.links.append(link)

    async def record_claim_usage(self, usage: ClaimUsage) -> ClaimUsage:
        return usage

    async def get_claim_usages(self, _claim_id: str) -> list[ClaimUsage]:
        return []


class InMemoryKnowledgeRepository(KnowledgeRepositoryPort):
    """In-memory knowledge repository for hermetic unit testing."""

    def __init__(self) -> None:
        self.versions: dict[str, list[KnowledgeObjectVersion]] = {}

    async def save_version(
        self, version: KnowledgeObjectVersion, _make_current: bool = True
    ) -> KnowledgeObjectVersion:
        if version.ko_id not in self.versions:
            self.versions[version.ko_id] = []
        self.versions[version.ko_id].append(version)
        return version

    async def get_version(self, ko_id: str, version: int) -> KnowledgeObjectVersion | None:
        for v in self.versions.get(ko_id, []):
            if v.version == version:
                return v
        return None

    async def get_current(self, ko_id: str) -> KnowledgeObjectVersion | None:
        vers = self.versions.get(ko_id, [])
        return vers[-1] if vers else None

    async def get_current_for_topic(self, topic_id: str) -> KnowledgeObjectVersion | None:
        for vers in self.versions.values():
            for v in reversed(vers):
                if v.topic_id == topic_id:
                    return v
        return None

    async def get_history(self, ko_id: str) -> list[KnowledgeObjectVersion]:
        return self.versions.get(ko_id, [])

    async def get_traceability_chain(self, claim_id: str) -> TraceabilityChain:
        raise NotImplementedError()


class InMemoryExecutionRepository:
    """In-memory execution repository for QuotaManager testing."""

    def __init__(self) -> None:
        self.calls: list[Any] = []
        self.quota: list[Any] = []

    async def record_model_call(self, call: Any) -> Any:
        self.calls.append(call)
        return call

    async def record_quota_consumption(self, entry: Any) -> Any:
        self.quota.append(entry)
        return entry


@pytest.mark.asyncio
async def test_research_agent_execution(tmp_path: Any) -> None:
    storage = LocalStorage(root_dir=str(tmp_path))
    source_repo = InMemorySourceRepository()
    search = FakeSearch()
    fetcher = FakeSourceFetcher()

    agent = ResearchAgent(
        search=search,
        source_fetcher=fetcher,
        storage=storage,
        source_repo=source_repo,
    )

    result = await agent.execute(topic_id="chess_origins", search_query="origin of chess", limit=2)

    assert result.topic_id == "chess_origins"
    assert result.sources_discovered > 0
    assert len(result.snapshots_created) > 0

    # Verify snapshot was stored in repository and blob storage
    snapshot_id = result.snapshots_created[0]
    snapshot = await source_repo.get_snapshot(snapshot_id)
    assert snapshot is not None
    assert snapshot.byte_size > 0
    blob = await storage.get(snapshot.storage_key)
    assert len(blob) > 0


@pytest.mark.asyncio
async def test_extraction_agent_execution(tmp_path: Any) -> None:
    storage = LocalStorage(root_dir=str(tmp_path))
    source_repo = InMemorySourceRepository()
    knowledge_repo = InMemoryKnowledgeRepository()
    exec_repo = InMemoryExecutionRepository()
    llm = FakeLlm()
    quota_mgr = QuotaManager(execution_repo=exec_repo)  # type: ignore[arg-type]

    # Create research snapshot first
    fetcher = FakeSourceFetcher()
    bytes_data, chash, mime = await fetcher.fetch("https://archive.org/details/chess")
    blob_key = await storage.put(bytes_data, mime)

    from atlas.domain.common.enums import SourceTier
    from atlas.platform.ids import generate_snapshot_id, generate_source_id
    from pydantic import HttpUrl

    source = Source(
        id=generate_source_id(),
        title="Chess History Archive",
        url=HttpUrl("https://archive.org/details/chess"),
        source_tier=SourceTier.PRIMARY,
        created_at=utc_now(),
    )
    await source_repo.save_source(source)

    snapshot = Snapshot(
        id=generate_snapshot_id(),
        source_id=source.id,
        content_hash=chash,
        storage_key=blob_key,
        byte_size=len(bytes_data),
        mime_type=mime,
        retrieved_at=utc_now(),
    )
    await source_repo.save_snapshot(snapshot)

    extraction_agent = ExtractionAgent(
        llm=llm,
        storage=storage,
        source_repo=source_repo,
        knowledge_repo=knowledge_repo,
        quota_mgr=quota_mgr,
    )

    result = await extraction_agent.execute(
        topic_id="chess_origins",
        topic_title="Origin of Chess",
        snapshot_id=snapshot.id,
        run_id="run_test_01",
        step_id="step_test_01",
    )

    assert result.claims_count == 2
    assert result.evidence_count == 2
    assert result.knowledge_object_id == "ko_chess_origins"
    assert result.ko_version == 1

    # Verify Knowledge Object was saved
    ko = await knowledge_repo.get_current_for_topic("chess_origins")
    assert ko is not None
    assert len(ko.claim_ids) == 2
    assert len(source_repo.evidence) == 2

    # Verify Claim Evidence links
    assert len(source_repo.links) == 2


@pytest.mark.asyncio
async def test_extraction_agent_increments_knowledge_object_version(tmp_path: Any) -> None:
    """Test W-05: Subsequent extractions for the same topic increment KO version."""
    storage = LocalStorage(root_dir=str(tmp_path))
    source_repo = InMemorySourceRepository()
    knowledge_repo = InMemoryKnowledgeRepository()
    exec_repo = InMemoryExecutionRepository()
    llm = FakeLlm()
    quota_mgr = QuotaManager(execution_repo=exec_repo)  # type: ignore[arg-type]

    fetcher = FakeSourceFetcher()
    bytes_data, chash, mime = await fetcher.fetch("https://archive.org/details/chess")
    blob_key = await storage.put(bytes_data, mime)

    from atlas.domain.common.enums import SourceTier
    from atlas.platform.ids import generate_snapshot_id, generate_source_id
    from pydantic import HttpUrl

    source = Source(
        id=generate_source_id(),
        title="Chess History Archive",
        url=HttpUrl("https://archive.org/details/chess"),
        source_tier=SourceTier.PRIMARY,
        created_at=utc_now(),
    )
    await source_repo.save_source(source)

    snapshot = Snapshot(
        id=generate_snapshot_id(),
        source_id=source.id,
        content_hash=chash,
        storage_key=blob_key,
        byte_size=len(bytes_data),
        mime_type=mime,
        retrieved_at=utc_now(),
    )
    await source_repo.save_snapshot(snapshot)

    extraction_agent = ExtractionAgent(
        llm=llm,
        storage=storage,
        source_repo=source_repo,
        knowledge_repo=knowledge_repo,
        quota_mgr=quota_mgr,
    )

    # First extraction creates version 1
    res1 = await extraction_agent.execute(
        topic_id="chess_origins",
        topic_title="Origin of Chess",
        snapshot_id=snapshot.id,
        run_id="run_v1",
        step_id="step_v1",
    )
    assert res1.ko_version == 1

    # Second extraction increments to version 2
    res2 = await extraction_agent.execute(
        topic_id="chess_origins",
        topic_title="Origin of Chess",
        snapshot_id=snapshot.id,
        run_id="run_v2",
        step_id="step_v2",
    )
    assert res2.ko_version == 2

    # Verify history has both versions
    history = await knowledge_repo.get_history("ko_chess_origins")
    assert len(history) == 2
    assert [v.version for v in history] == [1, 2]


@pytest.mark.asyncio
async def test_verification_agent_execution() -> None:
    source_repo = InMemorySourceRepository()
    exec_repo = InMemoryExecutionRepository()
    llm = FakeLlm()
    quota_mgr = QuotaManager(execution_repo=exec_repo)  # type: ignore[arg-type]

    from atlas.domain.common.enums import SourceTier
    from atlas.domain.knowledge.models import AssertionType, EvidenceStance
    from pydantic import HttpUrl

    source = Source(
        id="src_01",
        title="Chess History Archive",
        url=HttpUrl("https://archive.org/details/chess"),
        source_tier=SourceTier.PRIMARY,
        created_at=utc_now(),
    )
    await source_repo.save_source(source)

    evidence = Evidence(
        id="ev_01",
        source_id="src_01",
        snapshot_id="snp_01",
        locator="Section 1",
        quote="Earliest chess rules date to 6th-century India.",
        stance=EvidenceStance.SUPPORTS,
        confidence=1.0,
        extracted_at=utc_now(),
    )
    await source_repo.save_evidence(evidence)

    claim = Claim(
        id="clm_01",
        text="Chess originated in 6th-century India.",
        assertion_type=AssertionType.FACT,
        confidence=0.9,
        status=ClaimStatus.UNSUPPORTED,
        created_at=utc_now(),
    )
    await source_repo.save_claim(claim)

    agent = VerificationAgent(
        llm=llm,
        source_repo=source_repo,
        quota_mgr=quota_mgr,
    )

    outcome = await agent.verify_claim(
        claim_id="clm_01",
        evidence_id="ev_01",
        run_id="run_01",
        step_id="step_01",
    )

    assert outcome.claim_id == "clm_01"
    assert outcome.status == ClaimStatus.VERIFIED
    assert outcome.stance == EvidenceStance.SUPPORTS

    # Check updated claim in repository
    updated_claim = await source_repo.get_claim("clm_01")
    assert updated_claim is not None
    assert updated_claim.status == ClaimStatus.VERIFIED


@pytest.mark.asyncio
async def test_script_agent_execution() -> None:
    knowledge_repo = InMemoryKnowledgeRepository()
    source_repo = InMemorySourceRepository()
    exec_repo = InMemoryExecutionRepository()
    llm = FakeLlm()
    quota_mgr = QuotaManager(execution_repo=exec_repo)  # type: ignore[arg-type]

    from atlas.domain.knowledge.models import AssertionType, KnowledgeObjectStatus
    from atlas.domain.knowledge.payload import KnowledgePayloadV1

    claim = Claim(
        id="claim_01",
        text="Chaturanga was an ancient Indian four-division military game.",
        assertion_type=AssertionType.FACT,
        confidence=1.0,
        status=ClaimStatus.VERIFIED,
        created_at=utc_now(),
    )
    await source_repo.save_claim(claim)

    ko = KnowledgeObjectVersion(
        ko_id="ko_chess",
        version=1,
        topic_id="chess",
        status=KnowledgeObjectStatus.VERIFIED,
        actor_id="test",
        reason="verified knowledge",
        claim_ids=["claim_01"],
        payload=KnowledgePayloadV1(summary="Chess history summary."),
        created_at=utc_now(),
    )
    await knowledge_repo.save_version(ko)

    script_agent = ScriptAgent(
        llm=llm,
        knowledge_repo=knowledge_repo,
        source_repo=source_repo,
        quota_mgr=quota_mgr,
    )

    # 1. Test Angle Selection
    selected_angle = await script_agent.select_story_angle(
        ko_id="ko_chess",
        topic_title="Origin of Chess",
        run_id="run_01",
        step_id="step_01",
    )
    assert selected_angle == "The Court of Guptas"

    # 2. Test Script Generation
    result = await script_agent.generate_script(
        ko_id="ko_chess",
        topic_title="Origin of Chess",
        story_angle=selected_angle,
        run_id="run_01",
        step_id="step_02",
    )

    assert result.script is not None
    assert len(result.script.beats) > 0
    assert result.timing_plan is not None
    assert result.timing_plan.total_duration_seconds > 0.0

    # Enforce Invariant 1: all beats must carry claim IDs
    for beat in result.script.beats:
        assert len(beat.claim_ids) > 0
        assert "claim_01" in beat.claim_ids


@pytest.mark.asyncio
async def test_judge_agent_execution() -> None:
    knowledge_repo = InMemoryKnowledgeRepository()
    source_repo = InMemorySourceRepository()
    exec_repo = InMemoryExecutionRepository()
    llm = FakeLlm()
    quota_mgr = QuotaManager(execution_repo=exec_repo)  # type: ignore[arg-type]

    from atlas.domain.knowledge.models import AssertionType, KnowledgeObjectStatus
    from atlas.domain.knowledge.payload import KnowledgePayloadV1

    claim = Claim(
        id="claim_01",
        text="Chaturanga was an ancient Indian four-division military game.",
        assertion_type=AssertionType.FACT,
        confidence=1.0,
        status=ClaimStatus.VERIFIED,
        created_at=utc_now(),
    )
    await source_repo.save_claim(claim)

    ko = KnowledgeObjectVersion(
        ko_id="ko_chess",
        version=1,
        topic_id="chess",
        status=KnowledgeObjectStatus.VERIFIED,
        actor_id="test",
        reason="verified knowledge",
        claim_ids=["claim_01"],
        payload=KnowledgePayloadV1(summary="Chess history summary."),
        created_at=utc_now(),
    )
    await knowledge_repo.save_version(ko)

    script_agent = ScriptAgent(
        llm=llm,
        knowledge_repo=knowledge_repo,
        source_repo=source_repo,
        quota_mgr=quota_mgr,
    )
    script_res = await script_agent.generate_script(
        ko_id="ko_chess",
        topic_title="Origin of Chess",
        story_angle="The Court of Guptas",
        run_id="run_01",
        step_id="step_01",
    )

    judge = JudgeAgent(llm=llm, quota_mgr=quota_mgr)
    eval_res = await judge.evaluate_script(
        run_id="run_01",
        script=script_res.script,
        timing_plan=script_res.timing_plan,
        topic_title="Origin of Chess",
        step_id="step_02",
    )

    assert eval_res.report is not None
    assert len(eval_res.report.scores) == 8
    assert eval_res.weighted_score >= 78.0
    assert eval_res.passed is True
