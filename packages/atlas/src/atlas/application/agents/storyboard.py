import math

from atlas.application.ports.embedder import Embedder
from atlas.application.ports.media import ImageCandidate
from atlas.domain.media.models import MotionTreatment, Scene, Storyboard
from atlas.domain.script.models import Script, TimingPlan
from atlas.platform.clock import utc_now
from atlas.platform.ids import generate_id


def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    dot = sum(a * b for a, b in zip(v1, v2, strict=False))
    mag1 = math.sqrt(sum(a * a for a in v1))
    mag2 = math.sqrt(sum(b * b for b in v2))
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)


class StoryboardAgent:
    """Agent that pairs narrative beats to archival imagery to build a Storyboard."""

    def __init__(self, embedder: Embedder) -> None:
        self.embedder = embedder

    async def generate(
        self, script: Script, timing_plan: TimingPlan, candidates: list[ImageCandidate]
    ) -> Storyboard:
        """Pair each beat to the semantically closest image candidate."""
        if not candidates:
            raise ValueError("StoryboardAgent requires at least one ImageCandidate")

        # 1. Embed candidates
        candidate_texts = [f"{c.title} {c.author} {c.source_archive}" for c in candidates]
        candidate_embs = await self.embedder.embed_batch(candidate_texts)

        # 2. Embed beats
        beat_texts = [b.visual_cue or b.text for b in script.beats]
        beat_embs = await self.embedder.embed_batch(beat_texts)

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
