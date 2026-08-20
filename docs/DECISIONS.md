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

## Deferred, with the seam built

ORIGINS audience region, which sets the Channel audience clock (needed before Phase 8) · Speech and
narration · YouTube publishing and OAuth · WHY and HUMANS channels · semantic search
(bypass mode is the default until the graph earns its place) · long-form durations · multi-language ·
Temporal · OTel tracing · multi-user roles.
