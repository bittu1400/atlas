# Atlas System & Workflow Diagrams

This directory contains visual text diagrams (using ASCII box-drawing `+`, `-`, `|`, `/`, `\`) illustrating how Atlas is designed, organized, and executed.

> **These diagrams show intent as well as implementation.** Verified against the code on 2026-08-31:
> stage numbering and gate placement in `02` match `STAGE_SEQUENCE`; `01` names `StubRenderer`. Where
> a box names something that does not exist yet — Remotion rendering, real publishing, pgvector — the
> diagram says so inline. `docs/STATUS.md` §3 is the authority; a diagram is never one.

---

## 📑 Diagram Index

| Diagram | Description |
|---|---|
| [`01-system-architecture.md`](./01-system-architecture.md) | **Clean Architecture & Layers**: 4 inward-pointing layers, ports, adapters, and repositories |
| [`02-pipeline-workflow.md`](./02-pipeline-workflow.md) | **18-Stage Pipeline Lifecycle**: Flow from Idea Discovery to Final Render, automated steps, human gates, and structured rejection loops |
| [`03-traceability-and-database.md`](./03-traceability-and-database.md) | **Traceability & ER Schema**: Invariant 1 foreign-key tree (Assertion → Claim → Evidence → Source → Snapshot), append-only `claim_versions`, row-per-version KO mechanics, the Impact Index, and the production-artifact chain (script → timing plan → storyboard → render artifact) |
| [`04-execution-and-durability.md`](./04-execution-and-durability.md) | **State Machine & Durability**: Run/Step lifecycle, database row suspensions, GPU semaphore leases, and quota metering |
| [`05-focus-scoping-flow.md`](./05-focus-scoping-flow.md) | **Focus & Scoping**: Two-input operator model, Wikidata QID disambiguation, Domain research profiles, and by-value run capture |
| [`06-publishing-and-clocks.md`](./06-publishing-and-clocks.md) | **Publishing & The 4 Clocks**: UTC vs. Operator (`Asia/Kathmandu`) vs. Audience timezones, window allocation, and blackout enforcement |

---

## 📐 Design Principles Encoded in Diagrams

1. **Knowledge is the product; renderers are downstream.**
2. **Every statement resolves to primary source evidence enforced by PostgreSQL foreign keys.**
3. **Suspensions are database rows, consuming zero memory while awaiting human decisions.**
4. **Hardware constraints (8GB GPU) are serialized via managed semaphore leases.**
5. **Operator local time is never conflated with audience publishing time.**
