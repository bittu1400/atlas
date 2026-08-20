# Status

**Last updated:** 2026-08-20

This file exists to separate **decided** from **done**. Everything else in `docs/` records what Atlas
*will* be; this records where it actually stands. Update it at the end of every working session.

---

## 1. Where we are

**Phase 1 (Architecture) is complete.**
**Phase 2 (Database & Persistence) is complete and fully audited.**
**Phase 3 (Backend & State Machine) is complete and fully verified.**
- **FastAPI HTTP Application Layer (`apps/api/`)**: Full implementation of `/runs`, `/gates`, `/quota`, `/events` (Server-Sent Events), and `/health` endpoints with Pydantic request/response validation schemas, domain exception handling, and dependency injection wiring.
- **Background Worker Layer (`apps/worker/`)**: Pipeline execution worker entrypoint and Dramatiq task harness executing state machine runs.
- **Typer CLI Layer (`apps/cli/`)**: Command-line interface with 100% parity (`atlas run create/list/status`, `atlas gate list/approve/reject`, `atlas quota status`).
- **Durable 17-Stage State Machine Engine (`packages/atlas/src/atlas/application/pipeline/runner.py`)**: Traverses all 17 stages with step idempotency (`input_hash`), checkpointing, atomic GPU semaphore lease acquisition and TTL release (`ResourceLockTable`), and gate suspension/resumption.
- **Operator Gate & Structured Rejection Policy (`packages/atlas/src/atlas/application/policies/gate_policy.py`, `usecases/`)**: Automated and manual human review gates with mandatory structured feedback (`target_ref`, `rubric_dimension`, `reason`, `action`), transitioning runs to `REWORKING` or `ABANDONED` cleanly.
- **Quality Rubric & Licensing Enforcement (`packages/atlas/src/atlas/domain/quality/`, `policies/`)**: 100-point weighted scoring, hard gate (overall >= 78.0 and dimension floors >= 60.0), CC-BY/CC0/PD license verification, and AI image approval enforcement (Invariant 9).
- **Free-Tier Quota & Token Bucket Rate Limiter (`packages/atlas/src/atlas/platform/quota.py`)**: Sliding-window RPM, TPM, RPD, and TPD rate limit enforcement with deterministic cache key response caching.
- **68 unit, integration, and end-to-end tests passing** in ~6.1s against real PostgreSQL (`atlas_test`).
- **0 lint violations** and **0 strict mypy type errors across 109 source files**.

**Phase 4 (Frontend + Remotion Renderer) is ready to begin.** Scope includes the operator review UI (React 19, TypeScript, Tailwind, shadcn/ui, TanStack Query) and Remotion video rendering preview engine.

---

## 2. What exists

```
pyproject.toml       packages/atlas/src/atlas/domain/       tests/unit/
alembic.ini          packages/atlas/src/atlas/adapters/     tests/integration/
README.md            packages/atlas/src/atlas/platform/     docs/SPEC.md
CLAUDE.md            packages/atlas/src/atlas/application/  docs/ARCHITECTURE.md
docs/STATUS.md       docs/DECISIONS.md                      docs/GLOSSARY.md
docs/adr/            prompt.md                              var/
```

Git: `main`, remote `origin` at `https://github.com/bittu1400/atlas.git`, local only until pushed.

---

## 3. Verified environment

Probed 2026-07-30 on the development machine. **Re-verify rather than trust** — this is a snapshot.

| Component | State | Consequence |
|---|---|---|
| OS | Arch Linux, kernel 7.1.5 | — |
| GPU | RTX 5070 Laptop, 8151 MiB VRAM, driver 610.43 | Blackwell. Local Stable Diffusion needs a CUDA 12.8+ PyTorch build. 8 GB cannot host an LLM and an image model at once — hence the GPU lease in ADR-0001 |
| System Python | **3.14.6** | Ahead of much of the ML wheel ecosystem. **This is why D34 pins 3.13 via `uv`** — do not build against system Python |
| `uv` | installed | Will manage the pinned 3.13 interpreter |
| Node | **v26.5.0** | Ahead of Remotion's tested range; pin an LTS via `.nvmrc` before Phase 7 |
| `pnpm` | **not installed** | Required by D35 before any frontend or renderer work |
| Ollama | installed, **no models pulled** | See actions below |
| Docker | installed | Compose stack not yet written |
| FFmpeg | installed | — |
| Timezone | `Asia/Kathmandu`, UTC+05:45, no DST | This is the **operator** clock only. Never the publishing clock — see ADR-0007 |

---

## 4. Operator actions outstanding

Work only the operator can do. None of it blocks Phase 2.

| Action | Needed by | Notes |
|---|---|---|
| Obtain a **Google AI Studio API key** | Phase 5 | Separate product from a Gemini Advanced subscription, which grants no API access — see ADR-0004 context. Free tier |
| **Verify current free-tier limits** against live provider docs | Phase 5 | The quota budget in SPEC §11 is an estimate and must not be fixed until confirmed |
| `ollama pull qwen3:8b` and `ollama pull nomic-embed-text` | Phase 5 | Tier 1 models; both fit in 8 GB together |
| Install `pnpm`, pin Node LTS | Phase 4 | |
| Confirm the GitHub repo's **visibility** | now | The pushed commit contains the full product strategy and all ADRs |
| Delete the orphaned remote `master` branch if it exists, set `main` as default | now | Artifact of the local rename |
| Decide **backup and restore** (Postgres PITR + portable export bundle) | before first publication | Knowledge is the product and it is irreplaceable |

---

## 5. Open questions

Recorded in SPEC §16. Repeated here with the phase that forces the answer.

| Question | Needed by |
|---|---|
| ORIGINS **audience region** — sets the Channel's audience timezone | Phase 8 |
| Retention policy for snapshots and superseded renders | ~month 6 |
| Novelty threshold — cannot be set until a corpus exists | Phase 6 |
| Quality threshold of 78 — provisional until judge calibration | Phase 5 |
| Backup and restore approach | before first publication |

---

## 6. Known risks being carried deliberately

- **Remotion's commercial license ceiling.** Free for solo use, paid above a small team. The only
  dependency in the stack with this property. Exit path documented in ADR-0005; review before any team
  growth.
- **Free-tier dependency.** Limits and terms can change without notice. Provider independence is not a
  principle here, it is the continuity plan.
- **Hand-rolled durability primitives.** Retry, backoff, lease expiry, and stuck-run detection are ours to
  get right instead of Temporal's. ADR-0001 lists the triggers that should force the migration.
- **Quality priors are unvalidated.** The 78 threshold, the rubric weights, the pacing constants, and the
  seeded publishing windows are all reasoned starting points with no measured data behind them yet.
- **Storage grows monotonically** by design, ~500 MB per video. Retention policy required by month six.

---

## 7. Session log

| Date | Outcome |
|---|---|
| 2026-07-30 | Phase 1 completed. Vision reviewed against 38 identified gaps; D1–D38 settled; ADRs 0001–0007 written. Format changed from narrated 8-minute to 60-second text-and-sound-design. Budget fixed at zero. First channel changed from WHY to ORIGINS on archival imagery supply. Repo initialized, `main` pushed to GitHub. |
| 2026-08-20 | Phase 2 completed & triple-audited. Python 3.13 project initialized with `uv`. Alembic migrations established 25 normalized PostgreSQL tables with foreign-key traceability and CHECK constraints. 3-pass deep audit conducted and remediated (`docs/audit-2026-08-20.md`, `docs/audit-2026-08-20-second.md`, `docs/audit-2026-08-20-third.md`): strict Clean Architecture boundaries, async storage thread offloading, Alembic configuration URL routing, TOCTOU GPU lock race condition, typed models (`HttpUrl`, `date`), `TraceabilityChain` links, `ModelCall` parameters/code_version, and database check constraints. |
| 2026-08-20 | Independent audit (`gpt-audit.md`) conducted across P0, P1, and P2 findings. All issues 100% remediated and verified: (P0) A-01–A-05 schema mismatches, storage path traversal validation & atomic writes, snapshot composite FK integrity, and DB-level immutability triggers via `0002_remediate_p0` and `ADR-0008`; (P1) B-01–B-07 composite FK execution hierarchy (`gates`, `approvals`, `model_calls`), gate row locking with unique approvals constraint, KO atomic version sequential ordering, step idempotency uniqueness, atomic resource lock upsert with non-positive TTL checks, Wikidata QID uniqueness, snapshot storage key hash constraint via migration `697d28e88cb7`; (P2) C-01–C-06 timezone naive rejection, numeric bounds & intervals DB constraints, and batched single-query KO history retrieval. Full verification: 48 tests passing against PostgreSQL, 0 ruff violations, 0 mypy type errors across 56 files. Ready for Phase 3. |
| 2026-08-20 | Phase 3 completed. Full implementation of backend application layer (FastAPI), background worker layer (Dramatiq/Worker CLI), Typer CLI (`atlas run`, `atlas gate`, `atlas quota`), 17-stage state machine orchestrator (`PipelineRunner`), quality rubric and licensing policy engine, gate suspension/resumption use cases, structured rejection feedback, GPU semaphore leases, and free-tier quota manager with rate limiting. Verified with 68 tests passing against PostgreSQL, 0 ruff violations, and 0 mypy strict type errors across 109 source files. Ready for Phase 4. |
