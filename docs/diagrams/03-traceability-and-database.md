# 03 — Traceability Chain & Database Entity-Relationship Diagram

> **Verified against `adapters/persistence/tables.py` on 2026-08-31.** 30 tables. Two shapes
> changed that day: `claims` split into an identity row plus append-only `claim_versions`
> (**ADR-0015**), and four production-artifact tables were added (**ADR-0016**) — both are drawn
> below. There is still **no `blobs` table**: blobs live at `var/blobs/sha256/…` with no row, so
> there is no reference count and no deduplication bookkeeping (`ARCHITECTURE.md` §11.8, defect
> A-03).

This document visualizes the exact relational architecture implemented in PostgreSQL, demonstrating how Invariant 1 (*No fact without a source*) is enforced by database foreign keys rather than by application code.

---

## 1. Traceability Entity-Relationship Diagram

```
+---------------------------------------------------------------------------------------+
|                                  PRIMARY SOURCES & SNAPSHOTS                          |
|                                                                                       |
|  +------------------------+                     +-----------------------------------+ |
|  |     sources table      | 1                 * |         snapshots table           | |
|  +------------------------+-------------------->+-----------------------------------+ |
|  | PK  id                 |                     | PK  id                            | |
|  |     url                |                     | FK  source_id (RESTRICT)          | |
|  |     title              |                     |     content_hash (SHA-256)        | |
|  |     source_tier        |                     |     storage_key (var/blobs/...)   | |
|  |     created_at         |                     |     retrieved_at                  | |
|  +-----------+------------+                     +-----------------+-----------------+ |
|              |                                                    |                   |
+--------------|----------------------------------------------------|-------------------+
               | 1                                                1 |
               |                                                    |
               +-----------------------+   +------------------------+
                                       |   |
                                       v   v *
+---------------------------------------------------------------------------------------+
|                                    EVIDENCE & CLAIMS                                  |
|                                                                                       |
|                             +-----------------------------------+                     |
|                             |          evidence table           |                     |
|                             +-----------------------------------+                     |
|                             | PK  id                            |                     |
|                             | FK  source_id (RESTRICT)          |                     |
|                             | FK  snapshot_id (RESTRICT)        |                     |
|                             |     locator (p.14, col.2, para.3) |                     |
|                             |     quote (verbatim text)         |                     |
|                             |     stance (supports/contradicts) |                     |
|                             |     confidence                    |                     |
|                             +-----------------+-----------------+                     |
|                                               | 1                                     |
|                                               |                                       |
|                                               v *                                     |
|                             +-----------------------------------+                     |
|                             |       claim_evidence table        |                     |
|                             +-----------------------------------+                     |
|                             | PK,FK claim_id (CASCADE)          |                     |
|                             | PK,FK evidence_id (RESTRICT)      |                     |
|                             |       stance                      |                     |
|                             |       notes                       |                     |
|                             +-----------------+-----------------+                     |
|                                               | *                                     |
|                                               |                                       |
|                                               v 1                                     |
|                             +-----------------------------------+                     |
|                             |     claims table (IDENTITY ONLY)  |                     |
|                             +-----------------------------------+                     |
|                             | PK  id                            |                     |
|                             |     created_at                    |                     |
|                             +-----------------+-----------------+                     |
|                                               | 1                                     |
|                                               v *                                     |
|                             +-----------------------------------+                     |
|                             | claim_versions (APPEND-ONLY)      |                     |
|                             +-----------------------------------+                     |
|                             | PK,FK claim_id (CASCADE)          |                     |
|                             | PK    version                     |                     |
|                             |       text (atomic statement)     |                     |
|                             |       assertion_type (fact/infer) |                     |
|                             |       confidence                  |                     |
|                             |       status (unverified/verified/|                     |
|                             |         unsupported/refuted/      |                     |
|                             |         contested)                |                     |
|                             |       inferred_from_claim_ids     |                     |
|                             |       actor_id  <- who wrote it   |                     |
|                             |       reason    <- and why        |                     |
|                             |       created_at                  |                     |
|                             +-----------------------------------+                     |
|                             Current state = MAX(version). Nothing is                   |
|                             ever UPDATEd: Invariant 4, ADR-0015.                       |
|                             The identity row is what keeps claim_evidence,             |
|                             knowledge_object_claims and claim_usages stable            |
|                             across revisions.                                          |
|                                      +--------------------+                            |
+--------------------------------------|--------------------|---------------------------+
                                       | 1                  | 1
                                       |                    |
                                       |                    v *
+--------------------------------------|---+  +-----------------------------------------+
|      KNOWLEDGE OBJECT REVISIONS      |   |  |        IMPACT INDEX (RETRACTIONS)       |
|                                      |   |  |                                         |
|  +--------------------------------+  |   |  |  +------------------------------------+ |
|  | knowledge_object_claims table  |  |   |  |  |         claim_usages table         | |
|  +--------------------------------+  |   |  |  +------------------------------------+ |
|  | PK,FK ko_id                    |  |   |  |  | PK  id                             | |
|  | PK,FK version                  |  |   |  |  | FK  claim_id (RESTRICT)            | |
|  | PK,FK claim_id (RESTRICT) <----+  |   |  |  |     render_id                      | |
|  +---------------+----------------+  |   |  |  |     beat_id                        | |
|                  | *                 |   |  |  |     used_at                        | |
|                  |                   |   |  |  +------------------------------------+ |
|                  v 1                 |   |  |                                         |
|  +--------------------------------+  |   |  |  * Answers: "Which published videos    | |
|  | knowledge_object_versions table|  |   |  |    must be retracted/corrected if this  | |
|  +--------------------------------+  |   |  |    claim is later refuted?"             | |
|  | PK    ko_id                    |  |   |  +-----------------------------------------+
|  | PK    version (1, 2, 3...)     |  |   |
|  | FK    topic_id                 |  |   |
|  |       status (verified/draft)  |  |   |
|  |       quality_score            |  |   |
|  |       actor_id                 |  |   |
|  |       reason                   |  |   |
|  |       payload (JSONB v1)       |  |   |
|  +---------------+----------------+  |   |
|                  | 1                 |   |
|                  |                   |   |
|                  v 1                 |   |
|  +--------------------------------+  |   |
|  | knowledge_object_current table |  |   |
|  +--------------------------------+  |   |
|  | PK,FK ko_id                    |  |   |
|  | FK    current_version          |  |   |
|  |       updated_at               |  |   |
|  +--------------------------------+  |   |
+--------------------------------------+---+
```

---

## 2. Row-Per-Version Lifecycle

Knowledge Objects are **never edited in place**:

```
[ Research Generates KO ]
          |
          v
+-------------------------------------------------------------+
| knowledge_object_versions (ko_id="ko_42", version=1)        |
| - summary: "Tigers originated in East Asia ~2 Ma"           |
| - quality_score: 85.0                                       |
| - actor_id: "agent_researcher"                              |
| - created_at: 10:00 UTC                                     |
+-------------------------------------------------------------+
          |
          v
+-------------------------------------------------------------+
| knowledge_object_current (ko_id="ko_42")                    |
| - current_version: 1                                        |
+-------------------------------------------------------------+

          |
          |  [ Operator Revises with new findings ]
          v
+-------------------------------------------------------------+
| knowledge_object_versions (ko_id="ko_42", version=2)        |  <-- NEW ROW
| - summary: "Tigers originated in East Asia across corridor" |
| - quality_score: 92.0                                       |
| - actor_id: "operator_human"                                |
| - reason: "Refined narrative angle"                         |
| - created_at: 11:30 UTC                                     |
+-------------------------------------------------------------+
          |
          v
+-------------------------------------------------------------+
| knowledge_object_current (ko_id="ko_42")                    |  <-- POINTER UPDATED
| - current_version: 2                                        |
+-------------------------------------------------------------+

* Version 1 remains 100% immutable and queryable in history!
```

---

## 3. Production Artifacts (ADR-0016)

Stages 8 to 15 write these; stages 10 to 18 read them. Every arrow is a real foreign key, so
"which script did this render come from" is a join, not a guess. Each artifact is immutable — a
rewrite is a new ID, never an edit — and every row is scoped to its Run.

```
                            +---------------------------+
                            |          runs             |
                            +-------------+-------------+
                                          | 1
        +---------------------------------+---------------------------------+
        | *                               | *                               | *
+-------v-----------+           +---------v---------+            +----------v----------+
|     scripts       |           |   timing_plans    |            |    storyboards      |
+-------------------+           +-------------------+            +---------------------+
| PK id             |<--RESTRICT| PK id             |<--RESTRICT-| PK id               |
|    run_id  (FK)   |     +-----| FK script_id      |            | FK script_id        |
|    topic_id       |     |     |    total_duration |            | FK timing_plan_id   |
|    knowledge_     |     |     |    beat_timings   |            |    scenes    (JSON) |
|      object_id    |     |     |      (JSON)       |            |    render_targets   |
|    ko_version     |     |     |    caption_cues   |            |      (JSON)         |
|    story_angle    |     |     |      (JSON)       |            +----------+----------+
|    target_duration|     |     |    meta   (JSON)  |                       | 1
|    beats   (JSON) |     |     +-------------------+                       v *
|    created_at     |     |                                     +---------------------+
+-------------------+     |                                     |  render_artifacts   |
      ^                   |                                     +---------------------+
      |                   |                                     | PK id               |
      +-------------------+                                     | FK run_id           |
        one plan per script                                     | FK storyboard_id    |
                                                                |    render_target    |
  Beats carry claim_ids. The pre-render backstop walks           |    video_storage_key|
  every beat's claims and refuses to render unless each is       |    captions_storage_|
  VERIFIED with at least one claim_evidence row —                |      key            |
  PipelineRunner._assert_script_claims_are_traceable,            |    duration_seconds |
  raising UnapprovedScriptError. This is the last check          |    file_size_bytes  |
  before bytes leave the system (Invariants 1 & 2).              |    meta      (JSON) |
                                                                |    created_at       |
                                                                +---------------------+
                                                                UNIQUE(run_id, storyboard_id,
                                                                       render_target)
```

**Why the ordered sub-structures are JSON and not child tables.** Beats, beat timings, caption cues
and scenes are always read and written whole, through their parent, and are never queried across
artifacts. The one cross-artifact question — "which published outputs used this claim" — is already
answered by `claim_usages`. **D91** records this so it is a decision rather than a shortcut.
