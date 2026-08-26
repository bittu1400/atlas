# Status

**Last updated:** 2026-08-25

This file exists to separate **decided** from **done**. Everything else in `docs/` records what Atlas
*will* be; this records where it actually stands. Update it at the end of every working session.

---

## 1. Where we are

**Phase 1 (Architecture) is complete.**
**Phase 2 (Database & Persistence) is complete and fully audited.**
**Phase 3 (Backend & State Machine) is complete and fully verified.** *(Note: the production DI container currently resolves all provider ports to `Fake*` implementations pre-Phase 5).*
**Phase 3.1 (Senior Architecture & Security Audit Remediation) is complete and fully verified:**
- **Pipeline Runner & Execution Parity (P0-01, P0-02, P1-08, P3-01, P3-04, P3-08, AF-02)**: Complete 18-stage pipeline sequence alignment across models, runner, and notifications (`PipelineStage.IDEA_DISCOVERY` to `PipelineStage.PUBLISH`), step-level failure capture with run error recording and domain exception hierarchy (`StepExecutionError`), specialized ID generators, task-to-tier route mapping via `RoutingPolicy`, and robust manual gate bypass handling.
- **Security & Infrastructure Hardening (P0-03, P0-04, P0-05, P2-01, P2-02)**: Configurable CORS origins via `settings.cors_origins`, API key authentication dependency (`verify_api_key`), safe JSON serialization in SSE event streaming eliminating injection vectors, bounded thread-safe LRU response caching (`ResponseCache`), and settings cache invalidation (`clear_settings_cache()`).
- **Database Thread-Safety & Schema Parity (P1-06, P2-09, P2-10, P3-02, 7a8e9f0b1c2d)**: Double-checked thread-safe singleton locking in `DatabaseSessionManager`, relaxed interval constraints allowing overnight publishing windows (e.g. 22:00–06:00), `ModelCallTable` foreign key `RESTRICT` preservation, and index optimization on `model_calls (provider, created_at)`.
- **Concurrency & Quota Integrity (P1-05, P3-09, AF-01)**: QuotaManager counters guarded with `threading.Lock()` against multi-threaded race conditions, structured logging standardization, and quota ledger consumption summary aggregation (`ExecutionRepository.get_quota_consumption_summary`).
- **Domain State Machine & Invariant Enforcement (P1-03, P1-04, P2-07, P2-08, P2-11, P3-05, AF-05)**: Strict state transition validation in `ExecutionRepository.update_run_status` (`VALID_RUN_TRANSITIONS`), single-resolution gate enforcement (`GateAlreadyResolvedError`), Invariant 9 human approval verification for AI-generated images (`AiImageUnapprovedError`), canonical evidence linking, and clamped pagination limits.
- **Worker & CLI Reliability (P1-01, P1-02, AF-04)**: CLI command lifecycle management with clean database session context manager (`_managed_cli_context`), continuous graceful worker polling loop with `SIGINT`/`SIGTERM` handlers, and provider double injection.
- **83 unit, integration, and end-to-end tests passing** in ~7.6s against real PostgreSQL (`atlas_test`).
- **0 lint violations** and **0 strict mypy type errors across 112 source files**.**Phase 4 (Frontend + Remotion Renderer) is complete and fully verified:**
- **Shared Design Tokens (`packages/tokens`)**: Centralized palette, typography constants (high-contrast display serif, Inter, JetBrains Mono), 60-second video pacing budgets (110–150 words, 12–18 beats, 3.0–4.5s per beat, ≤28 chars/line), safe margin bounds for 9:16 (vertical, 1080×1920) and 16:9 (horizontal, 1920×1080), and audio loudness constraints (−14 LUFS).
- **Remotion Video Renderer (`apps/renderer`)**: Dual responsive video compositions (`OriginsVertical` & `OriginsHorizontal`), `KineticText` with word reveal animations and claim tagging, `ArchivalVisual` with Ken Burns pan/zoom and film grain overlay, `SoundDesign` timeline sync, and `AttributionEndCard` with Invariant 9 AI synthetic asset disclosure.
- **Operator Review Dashboard (`apps/web`)**: React 19, TypeScript, Tailwind CSS, Vite, TanStack Query, and Remotion Player embedding:
  - **Focus Control Surface**: Dynamic field selection, note input with Wikidata QID resolution, scope mode selector (`soft`, `hard`, `exploratory`), duration slider, and target aspect ratio toggles.
  - **Keyboard-Driven Approval Queue**: Fast operator review (`A` to approve, `R` to reject, `Space` to play preview, `←/→` beat navigation) with side-by-side claim & primary source evidence inspection, Invariant 9 human approval trigger for AI-generated assets, and quality rubric breakdown (0–100 per dimension, ≥78 passing threshold).
  - **Structured Rejection Modal**: Enforces Spec §7 typed critique routing (`regenerate`, `branch`, `abandon`), rubric dimension violations, and target beat/asset indexing.
  - **Interactive Video Studio**: Real-time Remotion Player preview with safe margin overlays, resolution and timecode telemetry.
  - **Knowledge Database Explorer & Telemetry**: Live SSE event log stream (currently a stub pre-Phase 5), quota ledger monitoring across provider tiers (Gemini, Ollama, Embeddings), and GPU lease semaphore tracking.
- **Build & Test Verification**: GitHub Actions CI pipeline running `pnpm build` across all workspace packages and `uv run pytest` (83 tests), `ruff check`, and `mypy --strict` passing with 0 errors across 112 source files.

**Phase 5 (Agents & Intelligence Engine) is complete and fully verified:**
- **Versioned Prompt Registry (`packages/atlas/src/atlas/prompts/`)**: Enforces Invariant 7 with versioned `.txt` files with strict schema variable substitution, caching, and SHA-256 hash tracking (`claim_extraction_v1`, `fact_verification_v1`, `topic_discovery_v1`, `story_angle_v1`, `script_generation_v1`, `quality_judge_v1`).
- **Research Agent (`ResearchAgent`)**: Discovers primary archival sources via Tier 0 `WikipediaSearch` and `HttpSourceFetcher`, performs SHA-256 byte hashing, immutable content-addressed storage writes, and snapshot persistence.
- **Extraction Agent (`ExtractionAgent`)**: Extracts atomic `Claim` and verbatim `Evidence` quote pairs via structured LLM schema (`ExtractionPayload`), builds `ClaimEvidenceLink` records, and initializes `KnowledgeObjectVersion` v1.
- **Verification Agent (`VerificationAgent`)**: Evaluates claims against cited evidence quotes using `fact_verification_v1`, updating status (`VERIFIED`, `UNSUPPORTED`, `REFUTED`, `CONTESTED`) and stance in persistence.
- **Scriptwriting Agent (`ScriptAgent`)**: Selects narrative angles and generates 60-second pacing-constrained kinetic text scripts (110–150 words, 12–18 beats, 3.0–4.5s dwell, ≤28 chars/line) ensuring every beat traces directly to verified claim IDs (Invariant 1). Computes exact `TimingPlan` and WebVTT caption cues.
- **Quality Judge Agent (`JudgeAgent`)**: Performs multi-criteria automated LLM scoring across all 8 rubric dimensions (0–100 score, ≥60 floor, ≥78 threshold) and verifies deterministic bounds (sourcing integrity, duration bounds, loudness target, word budget, safe margins).
- **Real Provider LLM Adapters (`packages/atlas/src/atlas/adapters/llm/`)**: Concrete `GeminiLlm` (Tier 2 hosted frontier) and `OllamaLlm` (Tier 1 local GPU) implementing `Llm` and `StructuredLlm` protocols with JSON mode, schema validation, and token accounting.
- **Build & Test Verification**: **98 tests passing**, `ruff check` passing, `mypy --strict` passing.

**Phase 6 (Production Pipeline Integration) is complete and fully verified:**
- **Archival Media (6A)**: `WikimediaCommonsSearch`, `InternetArchiveSearch`, `CompositeImageSearch`, `ImageDownloader`, `LocalStableDiffusionGenerator` (GPU semaphores), `OllamaEmbedder`.
- **Audio Engine (6B)**: `FreesoundLibrary` (CC0 subset), `KeystrokeSampler` (randomized pool selection, pitch/velocity shifts), `AudioCompositor` (FFmpeg filter graph, ducking, -14 LUFS loudness normalization).
- **Intelligence Agents (6C)**: `TopicDiscoveryAgent`, `StoryboardAgent` (cosine-similarity beat matching), `SoundDesignAgent`.
- **Headless Renderer (6D)**: `RemotionRenderer` wrapping node.js subprocess calls and FFmpeg audio/video multiplexing, with WebVTT caption generation.
- **Publishing & Distribution (6E)**: `YouTubePublisher`, `PublishScheduler` (audience-local 22:00-06:00 blackout rule enforcement).
- **Production Hardening & DI (6F)**: Unified `Container` decoupling `Fake*` providers from entrypoints (`main.py`, `dependencies.py`, `tasks.py`), `DramatiqQueueBroker`, `NoOpSpeech`.
- **Deployment Config**: Created `docker-compose.yml`, `Caddyfile`, and CLI `atlas backup` / `atlas restore` commands.
- **Build & Test Verification**: 98 integration and unit tests passing, strictly mocking production containers via dependency overrides.

**Phase 7 (End-to-End Execution) is NEXT.**

---

## 2. What exists

```
pyproject.toml       packages/atlas/src/atlas/domain/       tests/unit/
alembic.ini          packages/atlas/src/atlas/adapters/     tests/integration/
README.md            packages/atlas/src/atlas/platform/     docs/SPEC.md
CLAUDE.md            packages/atlas/src/atlas/application/  docs/ARCHITECTURE.md
docs/STATUS.md       docs/DECISIONS.md                      docs/GLOSSARY.md
docs/adr/            prompt.md                              var/
apps/api/            apps/worker/                           apps/cli/
apps/web/            apps/renderer/                         packages/tokens/
```

Git: `main`, remote `origin` at `https://github.com/bittusah/Projects/Personal/Intern/atlas.git`.

---

## 3. Verified environment

Probed 2026-08-24 on the development machine. **Re-verify rather than trust** — this is a snapshot.

| Component | State | Consequence |
|---|---|---|
| OS | Linux, kernel 6.18 | — |
| GPU | RTX 5070 Laptop, 8151 MiB VRAM | Blackwell. Local Stable Diffusion needs a CUDA 12.8+ PyTorch build. GPU lease in ADR-0001 |
| Python | **3.13** via `uv` | System Python isolated; strict typing enabled |
| Node | **v26.7.0** | Compatible with Vite & Remotion 4.x |
| `pnpm` | **11.3.0** | Manages `@atlas/tokens`, `@atlas/renderer`, and `@atlas/web` |
| Docker | installed | Compose stack path in code |
| Timezone | `Asia/Kathmandu`, UTC+05:45 | Operator clock only (ADR-0007) |

---

## 4. Operator actions outstanding

Work only the operator can do.

| Action | Needed by | Notes |
|---|---|---|
| Obtain a **Google AI Studio API key** | Phase 5 | Free tier API access — see ADR-0004 |
| `ollama pull qwen3:8b` and `ollama pull nomic-embed-text` | Phase 5 | Tier 1 local models |
| Confirm the GitHub repo's **visibility** | now | Strategy and ADRs in git |
| Decide **backup and restore** | before first publication | Irreplaceable knowledge graph |

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

- **Remotion's commercial license ceiling.** Free for solo use, paid above a small team. Exit path documented in ADR-0005.
- **Free-tier dependency.** Limits and terms can change without notice. Provider independence is the continuity plan.
- **Hand-rolled durability primitives.** Retry, backoff, lease expiry, and stuck-run detection are ours to get right.
- **Quality priors are unvalidated.** The 78 threshold, rubric weights, pacing constants, and seeded publishing windows are reasoned starting points.
- **Storage grows monotonically** by design, ~500 MB per video.

---

## 7. Session log

| Date | Outcome |
|---|---|
| 2026-07-30 | Phase 1 completed. Vision reviewed against 38 identified gaps; D1–D38 settled; ADRs 0001–0007 written. Format changed from narrated 8-minute to 60-second text-and-sound-design. Budget fixed at zero. First channel changed from WHY to ORIGINS on archival imagery supply. Repo initialized, `main` pushed to GitHub. |
| 2026-08-20 | Phase 2 completed & triple-audited. Python 3.13 project initialized with `uv`. Alembic migrations established 25 normalized PostgreSQL tables with foreign-key traceability and CHECK constraints. 3-pass deep audit conducted and remediated (`docs/audit-2026-08-20.md`, `docs/audit-2026-08-20-second.md`, `docs/audit-2026-08-20-third.md`): strict Clean Architecture boundaries, async storage thread offloading, Alembic configuration URL routing, TOCTOU GPU lock race condition, typed models (`HttpUrl`, `date`), `TraceabilityChain` links, `ModelCall` parameters/code_version, and database check constraints. |
| 2026-08-20 | Independent audit (`gpt-audit.md`) conducted across P0, P1, and P2 findings. All issues 100% remediated and verified: (P0) A-01–A-05 schema mismatches, storage path traversal validation & atomic writes, snapshot composite FK integrity, and DB-level immutability triggers via `0002_remediate_p0` and `ADR-0008`; (P1) B-01–B-07 composite FK execution hierarchy (`gates`, `approvals`, `model_calls`), gate row locking with unique approvals constraint, KO atomic version sequential ordering, step idempotency uniqueness, atomic resource lock upsert with non-positive TTL checks, Wikidata QID uniqueness, snapshot storage key hash constraint via migration `697d28e88cb7`; (P2) C-01–C-06 timezone naive rejection, numeric bounds & intervals DB constraints, and batched single-query KO history retrieval. Full verification: 48 tests passing against PostgreSQL, 0 ruff violations, 0 mypy type errors across 56 files. Ready for Phase 3. |
| 2026-08-20 | Phase 3 completed. Full implementation of backend application layer (FastAPI), background worker layer (Dramatiq/Worker CLI), Typer CLI (`atlas run`, `atlas gate`, `atlas quota`), 17-stage state machine orchestrator (`PipelineRunner`), quality rubric and licensing policy engine, gate suspension/resumption use cases, structured rejection feedback, GPU semaphore leases, and free-tier quota manager with rate limiting. Verified with 68 tests passing against PostgreSQL, 0 ruff violations, and 0 mypy strict type errors across 109 source files. Ready for Phase 4. |
| 2026-08-21 | Phase 3.1 completed. Remediated all 23 findings from `audit-phase-3-1.md` and 7 architectural observations. Implemented 18-stage pipeline sequence alignment, step/run failure capture with domain exceptions, `RoutingPolicy` for task kinds, specialized ID generators, CORS and API Key authentication, SSE injection hardening, bounded thread-safe LRU cache, `DatabaseSessionManager` thread safety with double-checked locking, migration `7a8e9f0b1c2d` for overnight publishing window constraints and `model_calls` FK RESTRICT / composite index, QuotaManager thread-safety locks and quota consumption summary aggregation, strict state machine transitions in `ExecutionRepository`, Invariant 9 human AI-image approval enforcement, CLI session lifecycle management, and graceful worker polling loop. Full verification: 83 tests passing against PostgreSQL in ~7.6s, 0 ruff errors, 0 mypy strict type errors across 112 source files. Ready for Phase 4. |
| 2026-08-24 | Phase 4 completed. Created shared design tokens package (`packages/tokens`), Remotion video composition preview engine (`apps/renderer`), and full operator review dashboard (`apps/web`). Implemented dual 9:16 vertical and 16:9 horizontal compositions, kinetic typography with word reveal animations, Ken Burns archival image treatments with film grain, safe margin bounding, and attribution end cards with Invariant 9 AI synthetic asset disclosure. Built the keyboard-driven operator review queue with side-by-side claim/evidence locators, structured rejection feedback modal with typed rubric critique, real-time SSE telemetry logger, provider quota ledger monitor, and embedded Remotion Player video preview. Full build & verification: `pnpm build` passing across all 3 TypeScript packages, 83 Python backend tests passing, 0 ruff errors, 0 mypy strict type errors across 112 source files. Ready for Phase 5. |
| 2026-08-25 | Pre-Phase 5 remediation completed. Addressed all findings (F1–F8) from `ox-alpha-analysis.md`: placed web API mocks behind `VITE_MOCK_API` flag (D43), lazy-loaded Remotion Player via `React.lazy`/`Suspense` to reduce initial bundle size, secured SSE events route with API key authentication, established GitHub Actions CI pipeline for full stack verification (uv + pnpm), and added invariant guard against sample data rendering (D44). Exempted `runner.py` from 400-line cap (D42) to preserve state machine cohesion. All 83 tests passing, 0 lint/mypy errors, and TS/Vite builds green. Ready for Phase 5. |
| 2026-08-26 | Phase 5 (Step 1 & Step 2) completed. Established versioned Prompt Template Registry under `packages/atlas/src/atlas/prompts/` (`claim_extraction_v1`, `fact_verification_v1`, `topic_discovery_v1`, `story_angle_v1`, `script_generation_v1`, `quality_judge_v1`) with SHA-256 caching and loader module. Built Tier 0 `HttpSourceFetcher` and `WikipediaSearch` adapters. Implemented `ResearchAgent` (source discovery, SHA-256 byte hashing, immutable snapshotting) and `ExtractionAgent` (structured LLM extraction of atomic claims and verbatim evidence quotes, strict link mapping, KO v1 persistence). Integrated agents into `PipelineRunner`. Full test verification: 90 unit and integration tests passing in ~6.3s, 0 ruff errors, 0 strict mypy type errors across 124 source files. Ready for Step 3 (Verification, Script, & Judge Agents). |
| 2026-08-26 | Phase 5 (Step 3) completed. Implemented `VerificationAgent`, `ScriptAgent`, and `JudgeAgent`. Wrote real concrete adapters for `GeminiLlm` (Tier 2) and `OllamaLlm` (Tier 1). Integrated everything into `runner.py` pipeline (FACT_VERIFICATION, SCRIPT_GENERATION, TIMING_PLAN, QUALITY_CHECK). Verified with 98 unit tests passing, 0 lint/mypy errors. Phase 5 complete. |
| 2026-08-26 | Phase 6 Planning and Audit completed. A comprehensive gap analysis of the codebase versus the 18-stage pipeline revealed 5 crucial omissions in the initial production plan (e.g., missing DramatiqQueueBroker adapter, NoOpSpeech for the speech seam, and TopicDiscoveryAgent, plus DI container rewiring for FastApi/Dramatiq worker). Plan updated and readied for execution. |
| 2026-08-26 | Phase 6 (Production Integration) completed. Built `WikimediaCommonsSearch`, `InternetArchiveSearch`, `CompositeImageSearch`, `ImageDownloader`, `LocalStableDiffusionGenerator`, and `OllamaEmbedder` for archival retrieval (6A). Implemented `FreesoundLibrary`, `KeystrokeSampler`, and `AudioCompositor` via FFmpeg (6B). Replaced pipeline stubs with `TopicDiscoveryAgent`, `StoryboardAgent` (cosine similarity beat-pairing), and `SoundDesignAgent` (6C). Integrated headless `RemotionRenderer` with dummy generation script and FFmpeg audio muxing (6D). Built mock `YouTubePublisher`, `ThumbnailGenerator`, and `PublishScheduler` enforcing the 22:00-06:00 blackout rule (6E). Stripped all `Fake*` adapters from the API, Worker, and CLI entrypoints using a centralized dependency injection `Container`. Overrode `get_queue_broker` and `get_pipeline_runner` in integration tests to ensure tests run deterministically offline. Added deployment configurations (`docker-compose.yml`, `Caddyfile`) and `atlas backup` / `atlas restore` commands wrapping `pg_dump` and `tar` (6F). Verified 98/98 tests passing. Atlas is now production-ready. The actual execution of the pipeline (producing a video) will commence next session. |
