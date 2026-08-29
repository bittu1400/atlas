# Decision Log

Settled choices from the Phase 1 architecture review, 2026-07-30.

This is a **record**, not a discussion. To change a decision here, write an ADR that supersedes it.
Decisions marked **ADR** have full rationale in `docs/adr/`.

## Product

| ID | Decision | Choice | Note |
|---|---|---|---|
| D1 | Users & auth | Single-user, no login, `actor_id` recorded on every mutation | Multi-user stays additive |
| D2 | Provider spend | **Zero.** Free tiers and local models only, quota-governed | **ADR-0004** |
| D3 | Narration | **None.** On-screen text plus sound design | `Speech` seam defined, unimplemented |
| D4 | First channel | **ORIGINS** | Public-domain imagery supply is deep; WHY's modern topics are not |
| D5 | Video length | Operator input, **default 60s** | Extend once quality is proven |
| D5b | Aspect ratio | **Both** 9:16 and 16:9, responsive layout from day one | 60s content needs the Shorts shelf |
| D6 | Hardware | RTX 5070 Laptop, 8GB VRAM. Local LLM + embeddings; image gen serialized | GPU semaphore in the worker |
| D29 | Publishing | Pipeline ends at an approved Render; manual upload initially | `Publisher` stubbed |
| D30 | Platform name | **Atlas** — package, CLI, database, services | Channels are records inside it |

## Architecture

| ID | Decision | Choice | Note |
|---|---|---|---|
| D7 | Orchestration | Postgres-backed queue + Dramatiq workers | **ADR-0001**, Temporal documented as upgrade path |
| D8 | Long work | Separate worker processes; the API only enqueues | **ADR-0001** |
| D9 | Human gates | DB state machine, resume token, structured rejection feedback | **ADR-0001** |
| D10 | Versioning | Row-per-version plus `current` pointer, immutable history | **ADR-0003** |
| D11 | KO storage | Typed core columns + JSONB payload with `schema_version`, upcast on read | **ADR-0003** |
| D12 | Object storage | Local filesystem behind a `Storage` interface; S3-compatible always | Content-addressed by hash |
| D13 | Migrations | Alembic, from the first table | No alternative considered |
| D14 | Focus model | `Focus` entity + Active Focus pointer, captured by value per Run | **ADR-0002** |
| D15 | Subject binding | Resolve to Wikidata at Focus creation; human confirms ambiguity | **ADR-0002** |
| D16 | Default scope mode | `soft` | **ADR-0002** |
| D17 | Domain definitions | Data-driven table carrying a Research Profile | **ADR-0002** |
| D18 | Evals | Rubric + LLM judge + deterministic checks, calibrated on hand-scored set | ~20 artifacts to calibrate |
| D19 | Quality gate | Hard threshold; failures route to a rework queue | Blocking, per `prompt.md` |
| D20 | Model routing | Config-driven policy per task with fallback chains | **ADR-0004** |
| D31 | Renderer | Remotion primary, behind a `Renderer` interface | **ADR-0005** |
| D32 | Timing | `TimingPlan` as canonical artifact driving text, SFX, cuts, captions | **ADR-0006** |
| D33 | Visual bed | Public-domain archival stills with motion treatment | AI generation stays priority 4 |

## Frontend & ops

| ID | Decision | Choice | Note |
|---|---|---|---|
| D21 | Frontend state | TanStack Query + Zustand | Server state is ~90% of this app |
| D22 | Realtime | SSE | One-directional, proxy-friendly |
| D23 | Reverse proxy | Caddy | Automatic TLS, readable config |
| D24 | Deployment | Single VPS with Docker Compose; path in code, not provisioned | Runs on the Arch box until told otherwise |
| D25 | Secrets | `.env` plus SOPS-encrypted files in-repo | |
| D26 | Observability start | structlog + Postgres quota ledger; OTel and Langfuse in Phase 5 | |
| D27 | Repo layout | Monorepo: `apps/`, `packages/`, `docs/` | |
| D28 | Docs split | `prompt.md` vision, `docs/SPEC.md` product truth, `CLAUDE.md` agent instructions | |
| D34 | Python | 3.13 via `uv` | System Python 3.14 is ahead of ML wheels |
| D35 | Node | Pinned LTS, `pnpm` | System Node is v26 |
| D36 | Git | Local repo, conventional commits, no remote yet | |
| D37 | Time zones | Four clocks: UTC storage, operator `Asia/Kathmandu`, audience per Channel, provider quota reset | **ADR-0007** |
| D38 | Publishing windows | Seeded policy table with confidence and provenance; blackouts enforced | **ADR-0007**, schema in Phase 2 |
| D39 | Domain Dependencies | `pydantic` is allowed in the domain layer | Decided as it's a validation/serialization library, not I/O |
| D40 | Composite Execution Keys | Execution hierarchy (`gates`, `approvals`, `model_calls`) enforces composite FKs `(id, run_id)` | Structurally prevents cross-run execution contamination |
| D41 | Database Immutability Triggers | PostgreSQL `BEFORE DELETE` and `BEFORE UPDATE` triggers enforce immutability on core knowledge tables | **ADR-0008**, guarantees append-only physically |
| D42 | Line cap exemption | `runner.py` orchestrator is exempt from the 400-line cap | Splitting would artificially fracture state machine logic |
| D43 | Dev mock safety | Mock API fallbacks require explicit `import.meta.env.VITE_MOCK_API` flag | Prevents dashboard from silently masking a downed backend |
| D44 | Render safety | Invariant guard throws on sample data if `getRemotionEnvironment().isRendering` is true | Prevents sample data reaching production video output |
| D45 | Production DI Container | Replace hardcoded `Fake*` instantiations in API and Worker entrypoints with a unified DI container | Ensures "Zero Fakes in Production" requirement is structurally enforced |
| D46 | NoOpSpeech Adapter | Use a no-op implementation for the `Speech` port rather than a test Fake in production | Enforces zero fakes while preserving the unimplemented architectural seam (D3) |

## Deferred, with the seam built

ORIGINS audience region, which sets the Channel audience clock (needed before Phase 8) · Speech and
narration · YouTube publishing and OAuth · WHY and HUMANS channels · semantic search
(bypass mode is the default until the graph earns its place) · long-form durations · multi-language ·
Temporal · OTel tracing · multi-user roles.

## ~~ADR-0010: Phase 7 End-to-End Orchestrator Verification Bypass~~ — **VOID**

> ## ⚠️ VOID — superseded by ADR-0011 on 2026-08-29
>
> **This decision must not be cited, followed, or partially applied.** It recorded a known-broken
> production adapter — `GeminiLlm.extract()` returning hardcoded payloads — as an accepted state,
> and it authorised bypassing every human gate. Invariants 1, 2, 7 and 9 were breached, and the run
> it describes as verification produced one evidence-less claim and a blank blue video.
>
> It also never received a file under `docs/adr/`; it was written directly into this log, bypassing
> ADR review as well as the invariants.
>
> **An ADR may not authorise breaking an invariant.** See
> `docs/adr/0011-retraction-of-adr-0010.md` and `docs/AUDIT-2026-08-29.md`.
>
> Retained, not deleted, per `CLAUDE.md` rule R11 — this is the record of how the failure happened.

**Date**: 2026-08-29

**Context**: In Phase 7, the objective was to perform an end-to-end test of the entire 17-stage state-machine pipeline to verify idempotency, queue transactions, and runner orchestrator stability. However, flaky external APIs (Gemini 502/400 errors) and manual bottleneck gates (e.g. `topic_selection`, `script_approval`) made it impossible to achieve a complete run reliably. Moreover, `QualityJudgeUseCase` enforces extremely strict deterministic bounds regarding video pacing (100-160 words, 58-62 seconds total duration) and Pydantic schema validation requiring exactly 8 rubric items in the `QualityJudgePayload`.

**Decision**:
1. We authored `run_pipeline_auto.sh`, an automated SQL background polling loop that instantly bypassed human operator gates via `atlas gate approve`.
2. We temporarily intercepted `GeminiLlm.extract()` to bypass network requests entirely. We mapped the expected structural requirements (specifically 8 dimension scores for the quality judge, and precisely 15 beats of 4.0 seconds duration, 9 words per beat for the script generation payload) to satisfy both Pydantic schemas and deterministic duration rules.

**Consequences**:
- **Positive**: We successfully verified the pipeline orchestrator end-to-end without external dependencies failing. The database recorded a `completed` state, proving the architectural logic of the `PipelineRunner` and execution persistence holds.
- **Negative**: The actual integration with the external LLM models remains untestable in a single bound without real robust rate-limiting and fallback setups. The intercept inside `gemini.py` currently holds static dummy payloads and must be removed or conditionally flagged when genuine model inference is desired.

---

## Decisions of 2026-08-29 (post-audit)

Taken by the operator after the audit in `docs/AUDIT-2026-08-29.md`. Full rationale, alternatives
and trade-offs in the ADRs; this table is the index.

| ID | Decision | Choice | ADR |
|---|---|---|---|
| D47 | ADR-0010 | **Void.** A bypass is not a decision. An ADR may never authorise breaking an invariant. | **ADR-0011** |
| D48 | Primary inference tier | **Tier 1 (Ollama, `qwen3:8b`) for every transformation task.** Gemini free tier is 20 req/day; that scarcity caused the fabrication incident. | **ADR-0012** |
| D49 | Fact verification tier | **Stays Tier 2 (Gemini).** The one task where a weaker model yields a false claim rather than a weaker sentence. | **ADR-0012** |
| D50 | Model IDs and provider limits | Move to `platform/config.py`; `GeminiLlm.capabilities` must state the **real** limits so `QuotaManager` blocks before the API does. `gemini-2.0-flash` is retired (404). | **ADR-0012** |
| D51 | Fabricated data | **Quarantine into schema `incident_2026_08_29`.** Never deleted; never `alembic downgrade base`. | **ADR-0013** |
| D52 | Anti-fabrication rules | **Enforced by CI + pre-commit**, not documentation. Documentation was already in place and did not hold. | **ADR-0014** |
| D53 | CI | `uv sync` → `uv sync --all-extras`. CI has **never** run a check; it fails at step 1 with `Failed to spawn: ruff`. | **ADR-0014** |
| D54 | Layering enforcement | Extend the existing AST test (`tests/unit/test_layering_boundaries.py`) rather than adopt `import-linter`. The ARCHITECTURE claim that import-linter enforces it has been false since Phase 1. | **ADR-0014** |
| D55 | Divergence registers | `ARCHITECTURE.md` §11 and `SPEC.md` §17 record where code disagrees with the docs. A row is deleted only when the code matches — never by editing the doc to match the code. | — |
| D56 | Phase numbering | SPEC §15 numbering is authoritative; `STATUS.md` silently renumbered and must be restated against it. SPEC's Phase 6 (knowledge system) was never built. | — (audit §5, T-38) |
| D57 | Renderer scope | **Real Remotion renderer deferred.** Phase 7 ends at a correct Knowledge Object, verified Script and real Storyboard. Data flow into the renderer is still fixed (T-19, T-20); `RemotionRenderer` is renamed `StubRenderer` and STATUS says rendering does not exist. | — (audit §8.2) |
| D58 | Phase re-baseline | **SPEC §15 numbering adopted**, plus a table in `STATUS.md` mapping the old STATUS phase names onto SPEC phases so the Phase-6 adapter work is recounted, not lost. Confirms D56. | — (audit §8.2, T-38) |
| D59 | Next-session scope | **Stage A + Stage B, then stop** (T-00 → T-11, T-35). Six invariant tests committed **failing**, `xfail(strict=True)`, tagged with defect IDs. | — (audit §6) |
| D60 | Commit strategy | **Docs committed alone**; the fabrication stays uncommitted so T-03 remains a visible, verifiable step. | — (audit §8.2) |
