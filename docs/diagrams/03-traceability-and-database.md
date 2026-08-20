# 03 — Traceability Chain & Database Entity-Relationship Diagram

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
|                             |           claims table            |                     |
|                             +-----------------------------------+                     |
|                             | PK  id                            |                     |
|                             |     text (atomic statement)       |                     |
|                             |     assertion_type (fact/infer)   |                     |
|                             |     confidence                    |                     |
|                             |     status (verified/unsupported) |                     |
|                             |     inferred_from_claim_ids       |                     |
|                             +--------+--------------------+-----+                     |
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
