# 04 — Execution State Machine & Durability Primitives

This document visualizes how Atlas manages pipeline execution, long-term human suspensions, hardware GPU serialization, idempotency checkpoints, and quota metering without requiring heavy external engines (ADR-0001).

---

## 1. Run & Gate Lifecycle State Machine

```
                      +-------------------+
                      |      pending      |
                      +---------+---------+
                                |
                                | Worker claims job
                                v
                      +-------------------+
                      |      running      |
                      +---+---+---+---+---+
                          |   |   |   |
             +------------+   |   |   +------------+
             | Gate Hit       |   | Quality Fail   | Crash / Error
             v                |   v                v
   +-------------------+      | +----------------+ +-------------------+
   |     suspended     |      | |   reworking    | |      failed       |
   | (Waiting on Human)|      | +-------+--------+ +---------+---------+
   +---------+---------+      |         |                    |
             |                |         | Re-try Angle       | Resume from
             | Human Decision |         v                    | Checkpoint
             |                |     (running)                v
             |                |                          (running)
             |                |
             +--------+-------+--------------------+
             |        |                            |
    Approved |        | Rejected (Abandon)         |
             v        v                            | All Steps Complete
         (running)  +-------------------+          v
                    |     abandoned     |  +-------------------+
                    +-------------------+  |     completed     |
                                           +-------------------+
```

---

## 2. Suspension is a Database Row (Zero Resource Consumption)

When a pipeline suspends at a manual gate, **no background process, connection, or thread is held**:

```
[ Worker executes Step ]
          |
          | Step hits Gate (e.g. Script Review)
          v
+-------------------------------------------------------------+
| 1. INSERT INTO gates (status="pending", gate_type="manual") |
| 2. UPDATE runs SET status="suspended"                       |
| 3. Worker process EXITS and returns to Dramatiq pool        |
+-------------------------------------------------------------+
          |
          | ... hours or days pass (0 bytes memory consumed) ...
          |
          v
[ Operator opens Web Dashboard / CLI and approves ]
          |
          v
+-------------------------------------------------------------+
| 1. INSERT INTO approvals (decision="approved", actor="bob") |
| 2. UPDATE gates SET status="approved", resolved_at=NOW()    |
| 3. UPDATE runs SET status="running"                         |
| 4. Enqueue next Step into Postgres queue                    |
+-------------------------------------------------------------+
```

---

## 3. GPU Semaphore Lease (`resource_locks`)

Atlas shares one laptop 8GB GPU between the local LLM (Ollama), local image generation, and Remotion Chromium rendering. Concurrent GPU access will crash with CUDA Out-of-Memory.

```
 Worker A (Local LLM)                    Worker B (Remotion Render)
         |                                           |
         | acquire_lock("gpu", ttl=60s)              |
         v                                           |
+------------------------------------+               |
| resource_locks table               |               |
| - resource_name: "gpu"             |               |
| - holder_id: "worker_a"            |               |
| - expires_at: 10:01:00 UTC         |               |
+------------------------------------+               |
         |                                           |
         | (Executing inference...)                  | acquire_lock("gpu")
         |                                           v
         |                               +------------------------+
         |                               | ResourceLockHeldError! |
         |                               | (Queued / Deferred)    |
         |                               +------------------------+
         |                                           |
         | release_lock("gpu")                       |
         v                                           v
+------------------------------------+   +------------------------+
| resource_locks row deleted / free  |-->| Worker B acquires lease|
+------------------------------------+   +------------------------+

* If a worker crashes, the TTL expires automatically, preventing deadlocks!
```

---

## 4. Quota Metering & Idempotency Key Flow

```
[ Step Triggered: (run_id="run_01", step="claim_extract", input_hash="sha_99") ]
                        |
                        v
          +-----------------------------+
          | Check IdempotencyKey Table  |
          +--------------+--------------+
                         |
        +----------------+----------------+
        | Found (Cached)                  | Not Found (First Run)
        v                                 v
+-----------------------------+   +-----------------------------+
| Return stored checkpoint    |   | Check Quota Ledger Budget   |
| (Cost: 0 tokens, 0 calls)   |   +--------------+--------------+
+-----------------------------+                  |
                                                 | Within Free-Tier Limits
                                                 v
                                  +-----------------------------+
                                  | Execute Model Call (Tier 2) |
                                  +--------------+--------------+
                                                 |
                                                 v
                                  +-----------------------------+
                                  | 1. INSERT INTO model_calls  |
                                  | 2. INSERT INTO quota_ledger |
                                  | 3. INSERT INTO idempotency  |
                                  | 4. Checkpoint output row    |
                                  +-----------------------------+
```
