# 02 — Pipeline Workflow (18 Stages & Gates)

This document visualizes the complete end-to-end production pipeline from Idea Discovery to Publication, including automated stages, human suspension gates, structured feedback loops, and checkpoints.

The numbering is `PipelineStage` / `STAGE_SEQUENCE` in `application/pipeline/runner.py`. It was renumbered from 17 to 18 stages on 2026-08-31 (**T-39, D101**) when SPEC §6 adopted the code's split of Script into generation and approval.

---

## 1. End-to-End Pipeline Map

```
  [ FOCUS ] (Domain + Subject Entity captured by value)
      |
      v
+-----------------------------+
| Stage 1: Idea Discovery     |  (Automatic - Tier 1 local clustering & relevance)
+--------------+--------------+
               |
               v
+=============================+
| Gate 2: Topic Selection     |  [MANUAL HUMAN GATE] -> Operator selects candidate Topic
+==============+==============+
               |
               +-------------------------------------------------------+
               | (Topic Approved)                                      |
               v                                                       |
+-----------------------------+                                        |
| Stage 3: Research           |  (Automatic - Tier 0 primary APIs:     |
|                             |   Archives, OpenAlex, Smithsonian)     |
|                             |  * All retrieved bytes snapshotted!    |
+--------------+--------------+                                        |
               |                                                       |
               v                                                       |
+-----------------------------+                                        |
| Stage 4: Claim Extraction   |  (Automatic - Tier 2 structured model  |
|                             |   extracts Claims + Evidence quotes)   |
+--------------+--------------+                                        |
               |                                                       |
               v                                                       |
+-----------------------------+                                        |
| Stage 5: Fact Verification  |  (Hybrid Gate - Flags contested        |
|                             |   contradictions for human review)     |
+--------------+--------------+                                        |
               |                                                       |
               v                                                       |
+=============================+                                        |
| Gate 6: Knowledge Object    |  [MANUAL HUMAN GATE]                   |
|         Review & Approval   |  Operator approves KO v1 or revises    |
+==============+==============+                                        |
               |                                                       |
               v                                                       |
+-----------------------------+                                        |
| Stage 7: Story Angle        |  (Hybrid - Generates narrative angles; |
|                             |   operator picks primary angle)        |
+--------------+--------------+                                        |
               |                                                       |
               v                                                       |
+-----------------------------+                                        |
| Stage 8: Script Generation  |  (Automatic - Writes ordered Beats;    |
|                             |   every Beat carries Claim IDs)        |
+--------------+--------------+                                        |
               |                                                       |
               v                                                       |
+=============================+                                        |
| Gate 9: Script Approval     |  [MANUAL HUMAN GATE]                   |
+==============+==============+                                        |
               |                                                       |
               +---------------------------+                           |
               | Approved                  | Rejected with Feedback    |
               v                           v                           |
+-----------------------------+   +-----------------------------+      |
| Stage 10: Timing Plan       |   | Regeneration / Branching    |------+
| (Pacing, dwell, word count) |   | (Consumes rubric critique)  |
+--------------+--------------+   +-----------------------------+
               |
               v
+-----------------------------+
| Stage 11: Asset Discovery   |  (Automatic - Searches Wikimedia Commons & archives;
|                             |   verifies license compatibility)
+--------------+--------------+
               |
               v
+=============================+
| Gate 12: Asset Selection    |  [MANUAL HUMAN GATE]
|          & License Approval |  * ALWAYS manual if AI image generation used!
+==============+==============+
               |
               v
+-----------------------------+
| Stage 13: Storyboard & Cuts |  (Automatic - Pairs Beats to Scene motion & focal crops)
+--------------+--------------+
               |
               v
+-----------------------------+
| Stage 14: Sound Design      |  (Automatic - Tactile keystrokes, ambient bed, SFX)
+--------------+--------------+
               |
               v
+-----------------------------+
| Stage 15: Remotion Render   |  (Automatic - GPU semaphore acquired;
|                             |   renders vertical 9:16 and horizontal 16:9)
+--------------+--------------+
               |
               v
+-----------------------------+
| Stage 16: Quality Check     |  (Automatic HARD GATE - Rubric score >= 78,
|                             |   no dimension < 60, zero unsourced claims)
+--------------+--------------+
               |
               +---------------------------+
               | Passed                    | Failed
               v                           v
+=============================+   +-----------------------------+
| Gate 17: Final Human Signoff|   | Quality Rework Queue        |
+==============+==============+   | (Re-routes with diagnostic) |
               |                  +-----------------------------+
               v
+-----------------------------+
| Stage 18: Publish           |  (Loads the persisted Render Artifacts and calls the
|                             |   Publisher once per aspect ratio, recording the IDs
|                             |   it returns. Today the Publisher is StubPublisher.)
+-----------------------------+
```

> **Verified against the code 2026-08-31.** Stage numbers and gate placement match
> `STAGE_SEQUENCE` and `DEFAULT_STAGE_GATES`. Two labels above describe intent rather than what
> runs: **stage 15** spawns no Remotion process — `StubRenderer` writes an ffmpeg colour field with
> real captions from the persisted Timing Plan — and **stage 18**'s publisher publishes nothing.
> `docs/STATUS.md` §3 is the authority on what does not exist.
>
> One nuance the boxes cannot show: stage 7's gate suspends *before* an angle exists, so the
> operator approves "proceed to scripting", not a named angle. The angle is selected inside stage 8
> (**D92**, SPEC §6).

---

## 2. Rejection & Learning Loop

When an operator rejects an artifact at a gate, plain rejection is rejected by the system. Typed feedback is required:

```
[ Operator Rejection at Gate ]
               |
               | Requires: { target_ref, rubric_dimension, reason, action }
               v
+-------------------------------------------------------------+
|                   RejectionFeedback Record                  |
|  - target_ref: "beat_02"                                    |
|  - rubric_dimension: "Hook strength"                        |
|  - reason: "Lead with exact year of archaeological finding" |
|  - action: REGENERATE | BRANCH | ABANDON                    |
+------------------------------+------------------------------+
                               |
            +------------------+------------------+
            |                                     |
            v                                     v
+--------------------------+          +--------------------------+
|  Regenerate with Context |          |  Branch from KO Angle    |
| (Feeds feedback as typed |          | (Explores fresh angle    |
|  input to attempt 2)     |          |  from existing verified  |
|                          |          |  Knowledge Object)       |
+--------------------------+          +--------------------------+
```
