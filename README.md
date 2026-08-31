# Atlas

An AI knowledge publishing platform.

Atlas researches a topic from primary sources, builds a canonical versioned **Knowledge Object** where
every factual statement is traceable to evidence, and renders that knowledge into publishable artifacts.

**Knowledge is the product. Every renderer is downstream of it.**

The first renderer produces 60-second silent-friendly videos: on-screen kinetic text over public-domain
archival imagery, carried by sound design rather than narration. Blogs, podcasts, newsletters, and other
formats are additional renderers over the same knowledge — not redesigns.

> **Status (measured 2026-08-31): SPEC phases 1–3 and 5 are complete; phase 4 is complete for the CLI
> and partial for the dashboard. Phases 6 (knowledge system) and 7 (rendering) are not started.**
> The pipeline runs all 18 stages end to end against deterministic fakes and asserts its own database
> state afterwards. **Rendering and publishing do not exist** — `StubRenderer` produces a flat colour
> field with real captions, `StubPublisher` publishes nothing.
> The dashboard reads the API and renders no fixtures, but **no test drives a browser**, so what it
> renders is unverified. Until 2026-08-31 five of its components displayed invented claims and
> invented provenance hashes; that is defect V-03 in the audit, and it is the reason to read the
> audit before trusting a screen.
> See [`docs/STATUS.md`](docs/STATUS.md) for the authoritative state and the raw command output
> behind every number. Do not quote a metric from this file; quote STATUS, after re-measuring.

---

## The discipline

One rule shapes the entire system:

**Atlas never invents a fact.** A language model here extracts, structures, ranks, phrases, and judges.
It never supplies knowledge. Every assertion that reaches an output resolves through claim → evidence →
source → archived snapshot, and that chain is enforced by database constraints rather than by convention.

Inferences are labelled as inferences. Opinions are labelled as opinions. Where sources conflict, both
are stored and the disagreement is preserved rather than resolved. Knowledge is append-only — nothing is
ever edited in place or deleted: a Claim is an immutable identity row plus a chain of `claim_versions`,
each naming the actor who wrote it and the reason
([ADR-0015](docs/adr/0015-append-only-claim-versions.md)).

This discipline was broken once, deliberately, by an agent looking for a shortcut. The incident, the
full defect register, and the guards that now make a repeat structurally detectable are in
[`docs/AUDIT-2026-08-29.md`](docs/AUDIT-2026-08-29.md). It is required reading before changing
anything.

---

## Documentation

| Document | What it is |
|---|---|
| [`docs/STATUS.md`](docs/STATUS.md) | **Start here.** Measured baseline, what exists, what does not, and the session close-out checklist |
| [`docs/AUDIT-2026-08-29.md`](docs/AUDIT-2026-08-29.md) | **Read second.** The fabrication incident, the defect register, and **§15.9** — the live task list in the order it should be worked |
| [`docs/SPEC.md`](docs/SPEC.md) | Product truth — format, quality rubric, licensing, pipeline, failure semantics |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Layering, folder map, **§2.1 the HTTP surface**, orchestration, provider ports, testing strategy |
| [`docs/GLOSSARY.md`](docs/GLOSSARY.md) | Ubiquitous language — one name per concept |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Settled choices, D1–D125, each pointing at its rationale |
| [`docs/adr/`](docs/adr/) | Architecture Decision Records — why, what was rejected, what it costs |
| [`CLAUDE.md`](CLAUDE.md) | Instructions for AI agents working in this repository |
| [`prompt.md`](prompt.md) | The original vision statement. Immutable — never edited |
| [`docs/archive/`](docs/archive/) | Superseded documents kept as evidence. Nothing in here is a current claim |

Every ADR states its trade-offs and the conditions that should reopen it. A decision without a recorded
cost and an expiry condition is a preference, not a decision.

---

## Constraints that shaped the design

- **Zero monetary cost.** Free deterministic sources, local models on one 8 GB GPU, and hosted free-tier
  models — in that order. Quota, not money, is the scarce resource. ([ADR-0004](docs/adr/0004-provider-ladder-and-quota.md))
- **Human approval at every stage that matters**, switchable to automatic per stage. A run suspends for
  days without holding a process, because gates are database rows. ([ADR-0001](docs/adr/0001-orchestration-and-durability.md))
- **Provider independence enforced by import direction.** No vendor SDK appears outside its adapter
  directory, so swapping a provider touches one folder.
- **Total CLI parity with the dashboard**, guaranteed structurally: both are thin adapters over the same
  application use cases, so a feature cannot exist in one and not the other.
- **Craftsmanship over quantity.** Roughly three videos per day, gated by a measurable quality
  threshold that blocks publication rather than merely reporting a score.

---

## Stack

Python 3.13 · FastAPI · Dramatiq · PostgreSQL · SQLAlchemy · Alembic ·
React 19 · TypeScript · Tailwind · TanStack Query · FFmpeg ·
Docker Compose · Caddy · pytest · ruff · mypy --strict

Planned but **not yet installed or invoked**, listed separately so this section cannot be read as a
claim: pgvector (no extension, no vector column), Remotion (the project exists in `apps/renderer/`
and its compositions build, but no node process is ever spawned by Atlas), Ollama (`OllamaEmbedder`
is wired and reachable at `OLLAMA_URL`; `OllamaLlm` is wired into nothing — audit tasks T-28, T-30),
shadcn/ui and Zustand (named in ARCHITECTURE §8 as the target; neither is installed).

`ffmpeg` is a **system** dependency, not a Python one: `StubRenderer` shells out to it. The
`Dockerfile` installs it; a local checkout needs it on `PATH` or the renderer test skips.

---

## Phases

Numbering is [`docs/SPEC.md` §15](docs/SPEC.md)'s. State measured 2026-08-31.

| | Phase | State |
|---|---|---|
| 1 | Architecture | **complete** |
| 2 | Database & Persistence | **complete** |
| 3 | Backend | **complete** |
| 4 | Frontend + CLI | **CLI complete; dashboard builds and reads the API, but no test drives a browser** |
| 5 | Agents | **complete** |
| 6 | Knowledge system — graph, entity binding, novelty, impact index | **not started** |
| 7 | Rendering — Remotion compositions, sound design, both targets | **not started** (deferred, D57) |
| 8 | Publishing | not started |
| 9 | Analytics | deferred |
| 10 | Optimization | deferred |

Acceptance criteria per phase are in [`docs/SPEC.md` §15](docs/SPEC.md); the mapping from the older,
different phase numbering this repository used until 2026-08-31 is in
[`docs/STATUS.md` §2.1](docs/STATUS.md).

---

## Working here

```bash
uv sync --all-extras                                  # --all-extras carries ruff, mypy, pytest, pre-commit
uv run ruff check . && uv run mypy . && uv run pytest
pnpm install && pnpm -r build                         # tokens, renderer, web
```

The suite needs a local PostgreSQL reachable at
`postgresql+asyncpg://postgres@localhost:5432/atlas_test` and applies its own migrations. Note that
`docker-compose.yml`'s `postgres` service is a *different* database (`atlas` / `atlas_db`) on the same
host port, so the two cannot run at once.

**`uv run pytest` is the gate for the TypeScript too.** Guards 8 and 9 in
`tests/unit/test_no_fabrication.py` scan `apps/web/src` and `apps/renderer/src` for fixtures and
fabricated provenance ([ADR-0017](docs/adr/0017-anti-fabrication-covers-the-operator-interface.md));
`pnpm build` will not catch them.

Agents working in this repository start at [`CLAUDE.md`](CLAUDE.md).
