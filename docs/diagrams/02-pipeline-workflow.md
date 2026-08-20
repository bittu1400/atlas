# 02 — Pipeline Workflow (17 Stages & Gates)

This document visualizes the complete end-to-end production pipeline from Idea Discovery to Publication, including automated stages, human suspension gates, structured feedback loops, and checkpoints.

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
| Gate 8b: Script Approval    |  [MANUAL HUMAN GATE]                   |
+==============+==============+                                        |
               |                                                       |
               +---------------------------+                           |
               | Approved                  | Rejected with Feedback    |
               v                           v                           |
+-----------------------------+   +-----------------------------+      |
| Stage 9: Timing Plan        |   | Regeneration / Branching    |------+
| (Pacing, dwell, word count) |   | (Consumes rubric critique)  |
+--------------+--------------+   +-----------------------------+
               |
               v
+-----------------------------+
| Stage 10: Asset Discovery   |  (Automatic - Searches Wikimedia Commons & archives;
|                             |   verifies license compatibility)
+--------------+--------------+
               |
               v
+=============================+
| Gate 11: Asset Selection    |  [MANUAL HUMAN GATE]
|          & License Approval |  * ALWAYS manual if AI image generation used!
+==============+==============+
               |
               v
+-----------------------------+
| Stage 12: Storyboard & Cuts |  (Automatic - Pairs Beats to Scene motion & focal crops)
+--------------+--------------+
               |
               v
+-----------------------------+
| Stage 13: Sound Design      |  (Automatic - Tactile keystrokes, ambient bed, SFX)
+--------------+--------------+
               |
               v
+-----------------------------+
| Stage 14: Remotion Render   |  (Automatic - GPU semaphore acquired;
|                             |   renders vertical 9:16 and horizontal 16:9)
+--------------+--------------+
               |
               v
+-----------------------------+
| Stage 15: Quality Check     |  (Automatic HARD GATE - Rubric score >= 78,
|                             |   no dimension < 60, zero unsourced claims)
+--------------+--------------+
               |
               +---------------------------+
               | Passed                    | Failed
               v                           v
+=============================+   +-----------------------------+
| Gate 16: Final Human Signoff|   | Quality Rework Queue        |
+==============+==============+   | (Re-routes with diagnostic) |
               |                  +-----------------------------+
               v
+-----------------------------+
| Stage 17: Publish Ready     |  (Outputs: .mp4 video files, WebVTT frame-accurate
|                             |   captions, provenance metadata & license end-cards)
+-----------------------------+
```

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
