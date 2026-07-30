# Atlas — Agent Instructions

This file tells you **how to work in this repository**. It is not the product vision.

| Document | What it is | Authority |
|---|---|---|
| `prompt.md` | The founder's original vision statement | Immutable. Never edit. Cite it, don't rewrite it. |
| `docs/SPEC.md` | Product truth — what Atlas does and what "correct" means | Authoritative for behaviour |
| `docs/ARCHITECTURE.md` | System structure, layering, module map | Authoritative for structure |
| `docs/adr/` | Why each major decision was made | Authoritative for rationale |
| `docs/GLOSSARY.md` | Ubiquitous language | Authoritative for naming |
| `docs/DECISIONS.md` | Log of settled choices (D1–D28) | Record; supersede via ADR only |
| `CLAUDE.md` | How to work here | This file |

**Read order before any non-trivial change:** `docs/SPEC.md` → relevant ADR → the code.

---

## What Atlas is, in one paragraph

Atlas researches a topic from primary sources, builds a canonical, versioned **Knowledge Object** where
every factual statement is traceable to evidence, and then renders that knowledge into publishable
artifacts. The first renderer produces 60-second silent-friendly videos: on-screen kinetic text over
public-domain archival imagery, carried by sound design rather than narration. **Knowledge is the
product. Every renderer is downstream of it.**

---

## Non-negotiable invariants

Violating any of these is a defect, regardless of whether tests pass.

1. **No fact without a source.** Every assertion that reaches an output carries claim IDs; every claim
   carries evidence IDs; every piece of evidence carries a source and a retrieval snapshot. If it
   cannot be traced, it does not ship.
2. **A model is never the source of a fact.** Language models extract, structure, rank, phrase, and
   judge. They do not supply facts. Unsupported claims are marked unsupported and dropped — never
   backfilled by asking a model what it remembers.
3. **Inference and opinion are labelled as such.** A claim carries an assertion type. Conflicting
   evidence is stored, both sides, never silently resolved.
4. **Knowledge is append-only.** Nothing is ever destroyed or edited in place. New version, new row,
   old row intact, provenance recorded.
5. **No provider SDK is imported outside its adapter.** `google.generativeai`, `ollama`, `openai`, and
   friends appear in exactly one directory each. Domain and application code depend on interfaces only.
6. **No hidden global mutable state.** Runs capture their configuration by value. The "active focus"
   is a default for new runs, never a variable read mid-run.
7. **Every artifact records how it was made** — provider, model ID, prompt version, parameters, input
   version, code version. "Rebuild this exactly" must always be answerable.
8. **Quota is a first-class resource.** Every model call is metered against the quota ledger before it
   is made. Atlas runs on free tiers; an unmetered call is a bug.
9. **AI-generated imagery always requires explicit human approval.** No exceptions, no auto-approve
   flag, no bypass in tests that could leak into production paths.
10. **Licenses are enforced, not recorded.** An asset whose license forbids the intended use is
    rejected by a gate, not flagged in a comment.

---

## Working agreement

- **Phase discipline.** Work the phase plan in `docs/SPEC.md`. Do not build Phase 5 machinery while
  Phase 2 is unfinished.
- **Explain, justify, then implement.** For any new module or architectural change: state the design,
  name the trade-off, note the alternative rejected — then write code.
- **An ADR is required** when you: introduce or replace a dependency, change a data model in a way that
  needs a migration, change the dependency direction between layers, add a provider category, or
  contradict an existing ADR. Supersede, never silently edit, a decided ADR.
- **Scope honesty.** If part of a task is blocked, finish everything else and say plainly what was left
  and why. Do not silently narrow scope.
- **No speculative generality.** Build the seam, not the unused implementation. One provider per
  category is enough until a second is genuinely needed.

---

## Code standards

**Python** — 3.13, managed by `uv`. `ruff` for lint and format. `mypy --strict`. Full type hints on
every signature. Docstrings on every public class and function, explaining *why* where non-obvious.
Pydantic models for all data crossing a boundary.

**TypeScript** — strict mode, no `any`, no non-null assertions without a comment justifying them.

**Both:**

- Files stay under ~400 lines. A longer file is a missing module.
- No class over ~200 lines. No function over ~50. If it wants to be bigger, it is two things.
- Names come from `docs/GLOSSARY.md`. If a concept has no glossary entry, add one before naming it.
- Comments explain *why*, never *what*. Delete any comment that restates the code.
- No duplicated logic. Second occurrence means extract.
- Errors are typed domain exceptions, never bare `Exception`, never a returned `None` meaning failure.
- Structured logging only — `logger.info("event.name", key=value)`. Never f-strings in log messages.

**Forbidden:**

- Business logic inside a FastAPI route handler. Routes parse, delegate, and serialize.
- Long-running work inside a request. It goes on the queue.
- Prompts as inline string literals. Prompts are versioned files under `prompts/`.
- `datetime.now()` without a timezone. UTC everywhere internally.
- Secrets, keys, or account identifiers in code, tests, fixtures, or logs.

---

## Layering rule

```
domain  ←  application  ←  adapters  ←  entrypoints
```

Dependencies point **inward only**. `domain/` imports nothing from Atlas outside itself and nothing
from any I/O library. If you need an import that breaks this, you need an interface instead.

See `docs/ARCHITECTURE.md` for the module map and the concrete folder layout.

---

## Testing

- **Unit tests never touch the network, the database, the filesystem, or a GPU.** Every provider has a
  deterministic fake. If a unit test needs a real provider, the seam is in the wrong place.
- **The full pipeline must run end-to-end in CI in seconds, for zero cost**, against fakes. This is a
  hard requirement, not an aspiration — it is the only thing that keeps e2e tests actually running.
- Real provider responses are captured as cassettes and replayed. Recording is an explicit, manual act.
- Every bug fix starts with a failing test that reproduces it.
- Test names state the behaviour: `test_rejects_claim_without_evidence`, not `test_claim_2`.

---

## Definition of done

A change is done when: types check, lint is clean, tests pass, a test covers the new behaviour, docs
and glossary are updated if concepts changed, an ADR exists if the change qualifies, structured logs
and quota accounting are wired for any new model call, and nothing in the invariant list above is
weakened.

---

## Commands

Populated as the toolchain lands. Do not invent commands that are not listed here.

```
# not yet implemented — Phase 2
```

---

## Things to never do here

- Never edit `prompt.md`.
- Never weaken an invariant to make a test pass.
- Never add a provider dependency to `pyproject.toml` without an ADR.
- Never commit generated media, model weights, or `.env`.
- Never mark a claim verified because a model asserted it.
- Never auto-approve an AI-generated image.
- Never introduce a second way to do something that already has a way.
