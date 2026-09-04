"""Repository for the production artifacts of a Run: Script, TimingPlan, Storyboard, RenderArtifact.

Stage 8 writes the Script that the stage 9 gate approves; stages 10-18 read it
back rather than regenerating. Persisting these artifacts is what makes
"rebuild this exactly" answerable (Invariant 7) and what lets the pre-render
backstop validate the script the operator actually saw.
"""

from typing import Any

from atlas.adapters.persistence.tables import (
    RenderArtifactTable,
    ScriptTable,
    StoryboardTable,
    TimingPlanTable,
)
from atlas.domain.media.models import RenderArtifact, RenderTarget, Scene, Storyboard
from atlas.domain.script.models import Beat, BeatTiming, CaptionCue, Script, TimingPlan
from atlas.platform.errors import ProductionArtifactNotFoundError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def _dump(models: list[Any]) -> list[dict[str, Any]]:
    """Serialize a list of frozen Pydantic models to JSON-safe dicts."""
    return [m.model_dump(mode="json") for m in models]


class ProductionRepository:
    """Data access repository for per-Run production artifacts."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # =========================================================================
    # Scripts
    # =========================================================================

    async def save_script(self, script: Script, run_id: str) -> Script:
        """Persist a Script. Scripts are never edited; a rewrite is a new Script ID."""
        self.session.add(
            ScriptTable(
                id=script.id,
                run_id=run_id,
                topic_id=script.topic_id,
                knowledge_object_id=script.knowledge_object_id,
                ko_version=script.ko_version,
                story_angle=script.story_angle,
                target_duration_seconds=script.target_duration_seconds,
                beats=_dump(list(script.beats)),
                created_at=script.created_at,
            )
        )
        await self.session.flush()
        return script

    async def get_script(self, script_id: str) -> Script:
        """Fetch a persisted Script by ID."""
        row = await self.session.get(ScriptTable, script_id)
        if not row:
            raise ProductionArtifactNotFoundError("Script", script_id)
        return Script(
            id=row.id,
            topic_id=row.topic_id,
            knowledge_object_id=row.knowledge_object_id,
            ko_version=row.ko_version,
            story_angle=row.story_angle,
            beats=[Beat.model_validate(b) for b in row.beats],
            target_duration_seconds=row.target_duration_seconds,
            created_at=row.created_at,
        )

    # =========================================================================
    # Timing Plans
    # =========================================================================

    async def save_timing_plan(self, plan: TimingPlan, run_id: str) -> TimingPlan:
        """Persist the canonical TimingPlan for a Script."""
        self.session.add(
            TimingPlanTable(
                id=plan.id,
                run_id=run_id,
                script_id=plan.script_id,
                total_duration_seconds=plan.total_duration_seconds,
                beat_timings=_dump(list(plan.beat_timings)),
                caption_cues=_dump(list(plan.caption_cues)),
                meta=dict(plan.metadata),
                created_at=plan.created_at,
            )
        )
        await self.session.flush()
        return plan

    async def get_timing_plan(self, timing_plan_id: str) -> TimingPlan:
        """Fetch a persisted TimingPlan by ID."""
        row = await self.session.get(TimingPlanTable, timing_plan_id)
        if not row:
            raise ProductionArtifactNotFoundError("TimingPlan", timing_plan_id)
        return TimingPlan(
            id=row.id,
            script_id=row.script_id,
            beat_timings=[BeatTiming.model_validate(t) for t in row.beat_timings],
            caption_cues=[CaptionCue.model_validate(c) for c in row.caption_cues],
            metadata=dict(row.meta or {}),
            created_at=row.created_at,
        )

    async def get_timing_plan_for_script(self, script_id: str) -> TimingPlan:
        """Fetch the TimingPlan belonging to a Script."""
        stmt = select(TimingPlanTable).where(TimingPlanTable.script_id == script_id)
        row = (await self.session.execute(stmt)).scalars().first()
        if not row:
            raise ProductionArtifactNotFoundError("TimingPlan for Script", script_id)
        return await self.get_timing_plan(row.id)

    # =========================================================================
    # Storyboards
    # =========================================================================

    async def save_storyboard(self, storyboard: Storyboard, run_id: str) -> Storyboard:
        """Persist a Storyboard binding Beats to selected archival assets."""
        self.session.add(
            StoryboardTable(
                id=storyboard.id,
                run_id=run_id,
                script_id=storyboard.script_id,
                timing_plan_id=storyboard.timing_plan_id,
                scenes=_dump(list(storyboard.scenes)),
                render_targets=[t.value for t in storyboard.render_targets],
                created_at=storyboard.created_at,
            )
        )
        await self.session.flush()
        return storyboard

    async def get_storyboard(self, storyboard_id: str) -> Storyboard:
        """Fetch a persisted Storyboard by ID."""
        row = await self.session.get(StoryboardTable, storyboard_id)
        if not row:
            raise ProductionArtifactNotFoundError("Storyboard", storyboard_id)
        return Storyboard(
            id=row.id,
            script_id=row.script_id,
            timing_plan_id=row.timing_plan_id,
            scenes=[Scene.model_validate(s) for s in row.scenes],
            render_targets=[RenderTarget(t) for t in row.render_targets],
            created_at=row.created_at,
        )

    # =========================================================================
    # Render Artifacts
    # =========================================================================

    async def save_render_artifact(self, artifact: RenderArtifact) -> RenderArtifact:
        """Persist one rendered output (one aspect ratio) for a Run."""
        self.session.add(
            RenderArtifactTable(
                id=artifact.id,
                run_id=artifact.run_id,
                storyboard_id=artifact.storyboard_id,
                render_target=artifact.render_target.value,
                video_storage_key=artifact.video_storage_key,
                captions_storage_key=artifact.captions_storage_key,
                duration_seconds=artifact.duration_seconds,
                file_size_bytes=artifact.file_size_bytes,
                meta=dict(artifact.metadata),
                created_at=artifact.created_at,
            )
        )
        await self.session.flush()
        return artifact

    async def get_render_artifact(self, artifact_id: str) -> RenderArtifact:
        """Fetch a persisted RenderArtifact by ID."""
        row = await self.session.get(RenderArtifactTable, artifact_id)
        if not row:
            raise ProductionArtifactNotFoundError("RenderArtifact", artifact_id)
        return self._artifact_to_domain(row)

    async def list_render_artifacts(self, run_id: str) -> list[RenderArtifact]:
        """List every rendered output for a Run, oldest first."""
        stmt = (
            select(RenderArtifactTable)
            .where(RenderArtifactTable.run_id == run_id)
            .order_by(RenderArtifactTable.created_at.asc())
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return [self._artifact_to_domain(r) for r in rows]

    @staticmethod
    def _artifact_to_domain(row: RenderArtifactTable) -> RenderArtifact:
        """Map a render_artifacts row onto its domain model."""
        return RenderArtifact(
            id=row.id,
            run_id=row.run_id,
            storyboard_id=row.storyboard_id,
            render_target=RenderTarget(row.render_target),
            video_storage_key=row.video_storage_key,
            captions_storage_key=row.captions_storage_key,
            duration_seconds=row.duration_seconds,
            file_size_bytes=row.file_size_bytes,
            metadata=dict(row.meta or {}),
            created_at=row.created_at,
        )
