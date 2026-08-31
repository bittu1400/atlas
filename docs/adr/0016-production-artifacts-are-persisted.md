# ADR-0016 — Scripts, timing plans, storyboards and render artifacts are persisted

**Status:** Accepted
**Date:** 2026-08-31
**Deciders:** operator
**Relates to:** Invariants 1, 7, 8; ADR-0006 (timing model); audit tasks T-18 → T-20; defects R-01, R-02, B3, B4
**Migration:** `b1c4d7e90a25_append_only_claims_and_production_artifacts`

## Context

Nothing produced by pipeline stages 8 through 15 was ever written to the database. There were no
`scripts`, `timing_plans` or `storyboards` tables and no repository that could have used them.

The runner compensated by regenerating. `ScriptAgent.generate_script()` was called from five
different stage handlers — `SCRIPT_GENERATION`, `TIMING_PLAN`, `STORYBOARD_CUTS`, `SOUND_DESIGN`
and `QUALITY_CHECK` — each producing a fresh `Script` with a fresh ID from a fresh model call. One
end-to-end run logged four distinct `script_id` values and metered four script-generation calls.

Three invariants broke as a result:

- **Invariant 7.** "Rebuild this exactly" was unanswerable: no artifact referenced a script that
  still existed anywhere.
- **The stage 9 gate was decorative.** The operator approved script A; the storyboard, the sound
  design, the render and the quality judgement were computed from scripts B, C, D and E. This is
  the same shape as the 2026-08-29 incident — a human decision recorded against an artifact that
  is then discarded.
- **Invariant 8.** Quota was charged five times for one script.

Downstream stages also conjured IDs by string formatting. `SOUND_DESIGN` composed against
`f"stb_{run.topic_id}"` while `StoryboardAgent` mints `generate_id("stb")`, so the soundtrack
referenced a storyboard that had never existed.

The pre-render invariant backstop (T-17) could not be written at all, and stood as an unconditional
`raise NotImplementedError("BLOCKED by T-18")` — stages 15 to 18 had never executed.

## Decision

Four tables, one repository, no regeneration.

```
scripts          (id, run_id, topic_id, knowledge_object_id, ko_version,
                  story_angle, target_duration_seconds, beats, created_at)
timing_plans     (id, run_id, script_id, total_duration_seconds,
                  beat_timings, caption_cues, meta, created_at)
storyboards      (id, run_id, script_id, timing_plan_id, scenes,
                  render_targets, created_at)
render_artifacts (id, run_id, storyboard_id, render_target, video_storage_key,
                  captions_storage_key, duration_seconds, file_size_bytes,
                  meta, created_at)
```

`ProductionRepository` owns them, behind `ProductionRepositoryPort`. Ordered sub-structures
(beats, timings, cues, scenes) are stored as JSON on the owning row: they are read and written
whole, always through their parent, and are never queried across artifacts.

Stage 8 selects the story angle, generates the Script and its TimingPlan, and persists both.
Stages 10 through 18 load what earlier stages checkpointed — the step's `output_artifact_ref` names
the artifact — and never call a model to reproduce it. Render artifacts are persisted per target
and the publish stage reads them back.

These artifacts are immutable, not versioned: a rewritten script is a new Script with a new ID.
Reworking a run after a rejection produces new rows, and the old rows stay.

## Alternatives considered

- **Blob storage keyed by content hash, with only the key in the database.** Rejected: the
  operator dashboard needs to list and filter scripts per run, and the pre-render backstop needs
  the beats' claim IDs. Both would become a fetch-and-parse of an opaque blob.
- **One generic `artifacts` table with a `kind` column and a JSON body.** Rejected: it cannot
  express `storyboards.script_id → scripts.id` as a foreign key, so the referential integrity that
  makes "which script did this render come from" answerable would live in application code.
- **Keeping regeneration but making it deterministic (temperature 0, cached).** Rejected: it makes
  the approved artifact and the rendered artifact *probably* equal rather than *necessarily* equal,
  and Invariant 1 does not admit "probably".

## Consequences

- The pipeline reaches stage 18. `REMOTION_RENDER` now runs the pre-output backstop against the
  persisted script: every claim cited by every beat must be `VERIFIED` and carry at least one
  evidence link, or the run fails with `UnapprovedScriptError`.
- One script-generation model call per run instead of five. The end-to-end test asserts this by
  counting `model_calls` rows.
- `PipelineRunner` takes a `production_repo` argument; every construction site must supply one.
- Two new typed errors: `ProductionArtifactNotFoundError` (a stage needed an artifact an earlier
  stage should have written) and `UnapprovedScriptError` (the backstop refused).
- Stage 7's `STORY_ANGLE` gate still suspends before any angle is chosen — the gate mechanism runs
  no handler for a suspending stage. The angle is selected at stage 8 by `select_story_angle`,
  replacing the hardcoded `"Origins and Preservation"` literal. Making the operator approve a
  *named* angle needs a change to gate mechanics and is not in this ADR.

## Trade-offs accepted

- JSON sub-structures cannot be queried directly. "Every beat citing claim X across all runs"
  requires a JSON path query or a future join table. `claim_usages` already covers the impact-index
  case this would otherwise serve.
- Asset candidates are still re-searched at stage 13 rather than persisted at stage 11, so the
  candidate list the operator approved at the stage 12 gate is not provably the list the storyboard
  drew from. The storyboard itself is persisted, so everything from stage 13 onward is stable. This
  gap is recorded in `docs/STATUS.md` and is not closed here.

## Revisit when

Asset selection needs to be provably the approved set (persist candidates at stage 11), or a
renderer that consumes the storyboard as structured input needs beat-level querying.
