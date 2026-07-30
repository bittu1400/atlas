# ADR-0001 — Orchestration and durability

**Status:** Accepted
**Date:** 2026-07-30
**Relates to:** D7, D8, D9

## Context

Atlas runs a long, multi-stage pipeline that suspends for human approval at several points. The
requirements are specific:

- A Run may pause at a gate for hours or days and must resume exactly where it stopped.
- Steps must be individually retryable and idempotent. A Render dying at 80% must not re-run research —
  both because it wastes an hour and because it would spend Tier 2 quota Atlas does not have.
- Work must never occupy a request handler. Renders take minutes; research takes longer.
- One 8GB laptop GPU is shared by the local LLM, local image generation, and Remotion's Chromium
  renderer. These must be serialized, so the scheduler needs to understand a resource constraint that no
  general-purpose queue knows about.
- Free-tier providers impose per-minute *and* per-day rate limits, so dispatch must be throttled against
  persisted, shared token buckets.

`prompt.md` names LangGraph as the agent framework. LangGraph orchestrates reasoning within an agent; it
is not a job system, and treating its checkpointer as durable infrastructure would conflate two concerns.

## Decision

**Postgres is the queue and the state store. Dramatiq workers execute Steps. Atlas owns the state
machine.**

- `runs`, `steps`, `gates`, `approvals`, `resource_locks`, `idempotency_keys` are Atlas tables with
  explicit states. The Run state machine is domain logic, not framework behaviour.
- A suspended Run is a row with status `suspended` and a gate reference. It holds no process, no
  connection, and no memory. Resumption is an insert of an approval plus a re-enqueue.
- Every Step carries an idempotency key of `(run_id, step_name, input_hash)`. A retried Step that already
  produced output returns the stored artifact rather than re-executing.
- Each Step persists its output artifact before marking itself succeeded, so checkpoints are real.
- GPU work acquires a named lease from `resource_locks` with a TTL and a priority. Leases expire, so a
  crashed worker cannot deadlock the GPU.
- Token buckets per provider are persisted in Postgres and shared across workers, tracking both the
  minute and day windows.
- The API only validates and enqueues. It never executes pipeline work.
- LangGraph is used *inside* individual agents where multi-step reasoning genuinely benefits from it. It
  never owns durability, scheduling, or gates.

## Alternatives considered

**Temporal.** Genuinely better at this problem — durable execution, signals for human-in-the-loop, and
suspension as a first-class concept rather than a table. Rejected for Phase 1 because it adds a server, a
worker SDK, versioning discipline, and an operational surface that one person maintaining a zero-budget
platform on a laptop cannot justify. It is the documented upgrade path, not a rejection on merit.

**Celery with Redis.** Mature and widely deployed, but it adds Redis as a second stateful dependency
purely for queueing, when Postgres is already present and gives transactional enqueue — the ability to
create a Run and enqueue its first Step in one atomic commit. Its result backend and state model would
also have to be worked around, since Atlas needs its own domain state machine regardless.

**LangGraph checkpointer alone.** Insufficient. No queue, no retry semantics, no rate limiting, no
resource leases, no multi-day suspension story, and it would tie infrastructure durability to an
AI-framework release cycle.

**FastAPI background tasks.** Not durable. A restart loses in-flight work, and there is no retry,
concurrency control, or visibility. Unacceptable for hour-long pipelines.

## Consequences

- Transactional enqueue: state changes and job dispatch commit together, so there is no window where a
  Run exists but was never queued.
- One stateful dependency, already required, already backed up.
- The full state machine is inspectable with SQL, which makes the Agent Monitor a query rather than an
  integration.
- Atlas must implement, test, and maintain retry, backoff, dead-lettering, lease expiry, and stuck-Run
  detection itself. This is real work and it must be tested deliberately, including the failure paths.
- A reaper process is required to expire abandoned leases and surface Runs stuck in `running`.

## Trade-offs accepted

We are hand-rolling durability primitives that Temporal would provide correctly out of the box, and we
will get some of them subtly wrong before tests catch it. We accept that cost in exchange for zero
additional infrastructure and complete visibility into a state machine we fully understand. Postgres as a
queue also does not scale to very high throughput — irrelevant at three Runs per day, disqualifying at
thousands.

## Revisit when

- Steps per Run exceed roughly 50, or the state machine needs branching that SQL states express poorly.
- Workers must span multiple machines.
- Suspensions routinely exceed a week, or approval workflows need timers, escalation, and reminders.
- Throughput exceeds roughly 100 Runs per day.

Any one of these is sufficient reason to migrate to Temporal. The Step-level idempotency and artifact
checkpointing designed here are exactly what makes that migration mechanical rather than a rewrite.
