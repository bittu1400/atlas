import math
from time import perf_counter

from atlas.application.policies.quota_policy import RoutingPolicy, TaskKind
from atlas.application.ports.embedder import Embedder
from atlas.application.ports.media import ImageCandidate
from atlas.domain.media.models import MotionTreatment, Scene, Storyboard
from atlas.domain.script.models import Script, TimingPlan
from atlas.platform.clock import utc_now
from atlas.platform.ids import generate_id
from atlas.platform.logging import get_logger
from atlas.platform.quota import QuotaManager

logger = get_logger("application.agents.storyboard")


def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    dot = sum(a * b for a, b in zip(v1, v2, strict=False))
    mag1 = math.sqrt(sum(a * a for a in v1))
    mag2 = math.sqrt(sum(b * b for b in v2))
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)


class StoryboardAgent:
    """Agent that pairs narrative beats to archival imagery to build a Storyboard."""

    def __init__(self, embedder: Embedder, quota_mgr: QuotaManager) -> None:
        self.embedder = embedder
        self.quota_mgr = quota_mgr

    async def generate(
        self,
        script: Script,
        timing_plan: TimingPlan,
        candidates: list[ImageCandidate],
        run_id: str = "run_unassigned",
        step_id: str | None = None,
    ) -> Storyboard:
        """Pair each beat to the semantically closest image candidate.

        An embedding is a model call, so both batches are metered against the
        quota ledger like any other (Invariant 8, defect V-02).
        """
        if not candidates:
            raise ValueError("StoryboardAgent requires at least one ImageCandidate")

        # 1. Embed candidates
        candidate_texts = [f"{c.title} {c.author} {c.source_archive}" for c in candidates]
        candidate_embs = await self._embed_metered(candidate_texts, run_id, step_id)

        # 2. Embed beats
        beat_texts = [b.visual_cue or b.text for b in script.beats]
        beat_embs = await self._embed_metered(beat_texts, run_id, step_id)

        scenes: list[Scene] = []
        used_candidate_ids: set[str] = set()

        timing_by_beat = {bt.beat_id: bt for bt in timing_plan.beat_timings}

        for i, (beat, beat_emb) in enumerate(zip(script.beats, beat_embs, strict=False)):
            best_candidate = None
            best_score = -999.0

            for cand, cand_emb in zip(candidates, candidate_embs, strict=False):
                score = _cosine_similarity(beat_emb, cand_emb)

                # Heavily penalize reusing the same image
                if cand.id in used_candidate_ids:
                    score -= 1.0

                if score > best_score:
                    best_score = score
                    best_candidate = cand

            # Should never happen due to the ValueError check, but for typing:
            if not best_candidate:
                best_candidate = candidates[0]

            used_candidate_ids.add(best_candidate.id)
            motion = MotionTreatment.SLOW_ZOOM_IN if i % 2 == 0 else MotionTreatment.SLOW_ZOOM_OUT
            timing = timing_by_beat[beat.id]

            scenes.append(
                Scene(
                    id=generate_id("scn"),
                    scene_index=i + 1,
                    beat_id=beat.id,
                    asset_id=best_candidate.id,
                    motion_treatment=motion,
                    start_time_seconds=timing.start_time_seconds,
                    duration_seconds=timing.end_time_seconds - timing.start_time_seconds,
                )
            )

        return Storyboard(
            id=generate_id("stb"),
            script_id=script.id,
            timing_plan_id=timing_plan.id,
            scenes=scenes,
            created_at=utc_now(),
        )

    async def _embed_metered(
        self, texts: list[str], run_id: str, step_id: str | None
    ) -> list[list[float]]:
        """Embed a batch, metering it against the quota ledger before and after."""
        route = RoutingPolicy.get_route(TaskKind.EMBEDDING)
        await self.quota_mgr.check_rate_limits(self.embedder.provider)

        started = perf_counter()
        embeddings = await self.embedder.embed_batch(texts)
        latency_ms = int((perf_counter() - started) * 1000)

        await self.quota_mgr.record_invocation(
            provider=self.embedder.provider,
            model_id=self.embedder.model_id,
            prompt_version="embedding_v1",
            parameters={"dimension": self.embedder.dimension, "batch_size": len(texts)},
            code_version="phase-5-v1",
            input_tokens=sum(len(t.split()) for t in texts),
            output_tokens=0,
            latency_ms=latency_ms,
            run_id=run_id,
            step_id=step_id,
        )
        logger.info(
            "storyboard.embedded_batch",
            provider=self.embedder.provider,
            model_id=self.embedder.model_id,
            batch_size=len(texts),
            route_tier=route.tier,
        )
        return embeddings
