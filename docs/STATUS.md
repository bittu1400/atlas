# Status

**Last updated:** 2026-08-20

This file exists to separate **decided** from **done**. Everything else in `docs/` records what Atlas
*will* be; this records where it actually stands. Update it at the end of every working session.

---

## 1. Where we are

**Phase 1 (Architecture) is complete.**
**Phase 2 (Database & Persistence) is complete and fully audited.**
**Phase 3 (Backend & State Machine) is complete and fully verified.**
**Phase 3.1 (Senior Architecture & Security Audit Remediation) is complete and fully verified:**
- **Pipeline Runner & Execution Parity (P0-01, P0-02, P1-08, P3-01, P3-04, P3-08, AF-02)**: Complete 18-stage pipeline sequence alignment across models, runner, and notifications (`PipelineStage.IDEA_DISCOVERY` to `PipelineStage.PUBLISH`), step-level failure capture with run error recording and domain exception hierarchy (`StepExecutionError`), specialized ID generators, task-to-tier route mapping via `RoutingPolicy`, and robust manual gate bypass handling.
- **Security & Infrastructure Hardening (P0-03, P0-04, P0-05, P2-01, P2-02)**: Configurable CORS origins via `settings.cors_origins`, API key authentication dependency (`verify_api_key`), safe JSON serialization in SSE event streaming eliminating injection vectors, bounded thread-safe LRU response caching (`ResponseCache`), and settings cache invalidation (`clear_settings_cache()`).
- **Database Thread-Safety & Schema Parity (P1-06, P2-09, P2-10, P3-02, 7a8e9f0b1c2d)**: Double-checked thread-safe singleton locking in `DatabaseSessionManager`, relaxed interval constraints allowing overnight publishing windows (e.g. 22:00–06:00), `ModelCallTable` foreign key `RESTRICT` preservation, and index optimization on `model_calls (provider, created_at)`.
- **Concurrency & Quota Integrity (P1-05, P3-09, AF-01)**: QuotaManager counters guarded with `threading.Lock()` against multi-threaded race conditions, structured logging standardization, and quota ledger consumption summary aggregation (`ExecutionRepository.get_quota_consumption_summary`).
- **Domain State Machine & Invariant Enforcement (P1-03, P1-04, P2-07, P2-08, P2-11, P3-05, AF-05)**: Strict state transition validation in `ExecutionRepository.update_run_status` (`VALID_RUN_TRANSITIONS`), single-resolution gate enforcement (`GateAlreadyResolvedError`), Invariant 9 human approval verification for AI-generated images (`AiImageUnapprovedError`), canonical evidence linking, and clamped pagination limits.
- **Worker & CLI Reliability (P1-01, P1-02, AF-04)**: CLI command lifecycle management with clean database session context manager (`_managed_cli_context`), continuous graceful worker polling loop with `SIGINT`/`SIGTERM` handlers, and provider double injection.
- **83 unit, integration, and end-to-end tests passing** in ~7.6s against real PostgreSQL (`atlas_test`).
- **0 lint violations** and **0 strict mypy type errors across 112 source files**.

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
| 2026-08-21 | Phase 3.1 completed. Remediated all 23 findings from `audit-phase-3-1.md` and 7 architectural observations. Implemented 18-stage pipeline sequence alignment, step/run failure capture with domain exceptions, `RoutingPolicy` for task kinds, specialized ID generators, CORS and API Key authentication, SSE injection hardening, bounded thread-safe LRU cache, `DatabaseSessionManager` thread safety with double-checked locking, migration `7a8e9f0b1c2d` for overnight publishing window constraints and `model_calls` FK RESTRICT / composite index, QuotaManager thread-safety locks and quota consumption summary aggregation, strict state machine transitions in `ExecutionRepository`, Invariant 9 human AI-image approval enforcement, CLI session lifecycle management, and graceful worker polling loop. Full verification: 83 tests passing against PostgreSQL in ~7.6s, 0 ruff errors, 0 mypy strict type errors across 112 source files. Ready for Phase 4. |

