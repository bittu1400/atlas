# Atlas

An AI knowledge publishing platform.

Atlas researches a topic from primary sources, builds a canonical versioned **Knowledge Object** where
every factual statement is traceable to evidence, and renders that knowledge into publishable artifacts.

**Knowledge is the product. Every renderer is downstream of it.**

The first renderer produces 60-second silent-friendly videos: on-screen kinetic text over public-domain
archival imagery, carried by sound design rather than narration. Blogs, podcasts, newsletters, and other
formats are additional renderers over the same knowledge — not redesigns.

> **Status: pre-implementation.** Phase 1 (architecture) is complete. There is no runnable code yet.
> See [`docs/STATUS.md`](docs/STATUS.md) for exactly what is decided versus what is done.

---

## The discipline

One rule shapes the entire system:

**Atlas never invents a fact.** A language model here extracts, structures, ranks, phrases, and judges.
It never supplies knowledge. Every assertion that reaches an output resolves through claim → evidence →
source → archived snapshot, and that chain is enforced by database constraints rather than by convention.

Inferences are labelled as inferences. Opinions are labelled as opinions. Where sources conflict, both
are stored and the disagreement is preserved rather than resolved. Knowledge is append-only — nothing is
ever edited in place or deleted.

---

## Documentation

| Document | What it is |
|---|---|
| [`docs/STATUS.md`](docs/STATUS.md) | **Start here.** Current phase, verified environment, outstanding actions |
| [`docs/SPEC.md`](docs/SPEC.md) | Product truth — format, quality rubric, licensing, pipeline, failure semantics |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Layering, folder map, orchestration, provider ports, testing strategy |
| [`docs/GLOSSARY.md`](docs/GLOSSARY.md) | Ubiquitous language — one name per concept |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Settled choices, D1–D38, each pointing at its rationale |
| [`docs/adr/`](docs/adr/) | Architecture Decision Records — why, what was rejected, what it costs |
| [`CLAUDE.md`](CLAUDE.md) | Instructions for AI agents working in this repository |
| [`prompt.md`](prompt.md) | The original vision statement. Immutable — never edited |

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

Python 3.13 · FastAPI · Dramatiq · PostgreSQL with pgvector · SQLAlchemy · Alembic ·
React 19 · TypeScript · Tailwind · shadcn/ui · TanStack Query · Remotion · FFmpeg ·
Ollama · Docker Compose · Caddy · pytest

---

## Phases

| | Phase | State |
|---|---|---|
| 1 | Architecture | **complete** |
| 2 | Database | next |
| 3 | Backend | |
| 4 | Frontend + CLI | |
| 5 | Agents | |
| 6 | Knowledge system | |
| 7 | Rendering | |
| 8 | Publishing | deferred |
| 9 | Analytics | deferred |
| 10 | Optimization | deferred |

Acceptance criteria per phase are in [`docs/SPEC.md` §15](docs/SPEC.md).
