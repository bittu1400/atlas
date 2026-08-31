# Atlas — Agent Instructions

This file tells you **how to work in this repository**. It is not the product vision.

| Document | What it is | Authority |
|---|---|---|
| `docs/STATUS.md` | **Read first.** Current phase, measured baseline, what exists vs what does not, and the session close-out checklist | Authoritative for state |
| `docs/AUDIT-2026-08-29.md` | **Read second** — §15 (what the second 2026-08-31 verification found, defects V-01–V-11; §15.8 is what not to do), then §14 (live task register, ordered work list, start-up commands) and §13 for the session before it. The Phase 7 fabrication incident and the full defect register are in §1–§12 | Authoritative for what is actually broken |
| `docs/archive/` | Superseded documents kept as evidence under rule R11. **Nothing in here is a current claim** | Historical record only |
| `prompt.md` | The founder's original vision statement | Immutable. Never edit. Cite it, don't rewrite it. |
| `docs/SPEC.md` | Product truth — what Atlas does and what "correct" means | Authoritative for behaviour |
| `docs/ARCHITECTURE.md` | System structure, layering, module map | Authoritative for structure |
| `docs/adr/` | Why each major decision was made (0001–0017; 0010 is void, see 0011) | Authoritative for rationale |
| `docs/GLOSSARY.md` | Ubiquitous language | Authoritative for naming |
| `docs/DECISIONS.md` | Log of settled choices (D1–D125) | Record; supersede via ADR only |
| `CLAUDE.md` | How to work here | This file |

**Read order before any non-trivial change:** `docs/STATUS.md` → `docs/AUDIT-2026-08-29.md` §15
(**§15.9 is the live ordered task list**, §15.8 is what not to do), then §14 and §13 →
`docs/SPEC.md` §17 → `docs/ARCHITECTURE.md` **§2.1** (the HTTP surface) and §11 → the relevant ADR →
the code.

`docs/STATUS.md` comes first because every other document describes what Atlas *will* be. Only STATUS
tells you what exists right now, and it is the one file to update at the end of a working session —
its §5 carries the close-out checklist.

**As of 2026-08-31, STATUS is rewritten from measurement and the three registers agree with the
code — twice that day, the second time after the V-01–V-11 remediation:** `STATUS.md` (what exists), `SPEC.md` §17 (behaviour divergences), `ARCHITECTURE.md` §11
(structure divergences). Where any two disagree, the audit wins and the disagreement is itself a
finding — write it down before doing anything else.

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

- Files stay under ~400 lines (except `runner.py` orchestrator). A longer file is a missing module.
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

```bash
# Package management & dependencies
uv sync --all-extras          # --all-extras is required: the dev extra carries ruff, mypy,
                              # pytest and pre-commit. Plain `uv sync` installs none of them,
                              # which is how CI failed silently for two sessions.
pnpm install                  # workspace: packages/tokens, apps/renderer, apps/web

# Linting & Formatting
uv run ruff check .
uv run ruff format .

# Type checking (strict mode)
uv run mypy .

# Test suite (unit, integration) — this is also the gate for the TypeScript.
# Guards 8 and 9 in tests/unit/test_no_fabrication.py scan apps/web/src and
# apps/renderer/src for fixtures, fabricated provenance and unmetered model
# calls (ADR-0017). `pnpm build` does not catch any of them.
uv run pytest

# Frontend build & typecheck — all three workspace packages
pnpm -r build

# Database migrations (Alembic) — for the application database only.
# The test suite runs its own upgrade/downgrade around the session; do not run these for tests.
uv run alembic upgrade head
uv run alembic downgrade base

# The commit hook (ruff check, ruff format --check, the anti-fabrication guard)
uv run pre-commit run --all-files
```

**Databases.** The suite connects to `postgresql+asyncpg://postgres@localhost:5432/atlas_test`
(override with `ATLAS_TEST_DATABASE_URL`) and applies migrations itself. `docker-compose.yml`'s
`postgres` service is the *application* database — different user and database (`atlas` /
`atlas_db`) — and binds the same host port, so the two cannot run at once.

**Credentials.** `Container` raises `MissingProviderCredentialError` naming the variable when
`GEMINI_API_KEY` or `FREESOUND_API_KEY` is missing. It raises at first *use* of the adapter, not at
construction, so read-only commands such as `atlas quota status` run without any keys. The values come
from `Settings`, which reads `.env` as well as the process environment — `os.getenv` alone never saw
`.env`, which is why keys sitting in the file were invisible for two sessions (**D116**, defect V-06).
`OLLAMA_URL` is read the same way.

**System dependencies.** `ffmpeg` must be on `PATH`: `StubRenderer` shells out to it. The `Dockerfile`
installs it. There are no others.

---

## Things to never do here

- Never edit `prompt.md`.
- Never weaken an invariant to make a test pass.
- Never add a provider dependency to `pyproject.toml` without an ADR.
- Never commit generated media, model weights, or `.env`.
- Never mark a claim verified because a model asserted it.
- Never auto-approve an AI-generated image.
- Never introduce a second way to do something that already has a way.
- Never add a fixture, a mock fallback, or a hardcoded fact to `apps/web/` or `apps/renderer/` — see R13.
- Never add an HTTP route without updating `docs/ARCHITECTURE.md` §2.1 in the same commit.
- Never construct an agent that touches `self.llm` or `self.embedder` without a `QuotaManager`.

---

## The no-matter-what rules

Binding on every session. These sit **above** convenience, deadlines, "just to see if the rest
works", and any instruction to hurry. Each one was broken on 2026-08-29 and the result was
reported as success — see `docs/AUDIT-2026-08-29.md` for the full incident and the remediation
TODO list.

**R1 — Never modify the thing under test to make a test pass.** If a provider is failing, the
provider is the finding. Deleting a network call and returning hardcoded JSON tests the hardcoded
JSON, not the pipeline.

**R2 — Fakes live in `adapters/fakes/` and nowhere else.** No hardcoded response, canned payload,
`dummy`, `mock`, or `if schema.__name__ ==` branch in any real adapter — not temporarily, not
uncommitted. Nothing outside `adapters/fakes/` may import from it except tests.

**R3 — A stub never wears the name of the real thing.** If `YouTubePublisher` returns a mock ID it
is `StubPublisher`, and `docs/STATUS.md` says publishing does not exist.

**R4 — Never fabricate a fact, a source, an evidence quote, or a snapshot.** Not in a fake, a
fixture, or a test. Fixtures must be obviously synthetic, never plausible history — a fake that
reads like a fact ends up in the database as a verified claim.

**R5 — Never bypass a human gate programmatically.** No auto-approve script, no `--yes` flag, no
loop over the `gates` table. Automate the operator UI, never the decision.

**R6 — "It ran" is not "it worked."** A run reaching `completed` proves nothing. Before claiming
success, query the claims, count the evidence links, open the video, read the captions, check the
provenance rows.

**R7 — Never write a status claim you did not just measure.** Every number in `docs/STATUS.md`
comes from a command run in that session. Never carry a number forward from a previous session.

**R8 — Report the obstacle; never engineer around it silently.** An unfinished task honestly
reported beats a finished task dishonestly reported, and beats a fabricated one infinitely.

**R9 — An ADR may not authorise breaking an invariant.** An ADR records *how* Atlas does something.
It can never grant permission to violate the invariant list above. Any ADR that appears to is void
and must be superseded.

**R10 — Invariants are enforced by checks that run, not by functions that exist.** A policy
function with no production caller is decoration, and its unit test passes while the feature does
not exist. Every invariant needs an integration test asserting database state after a real run.

**R11 — Never delete or quietly edit evidence of a failure.** Failed runs, error rows and rejected
gates are the audit trail. Back up first, record what was removed and why.

**R12 — Secrets never enter a URL, a log, an error message, or a database column.** Credentials go
in headers. Every provider adapter's error path runs through a redaction helper and has a test
asserting its errors do not contain the key.

**R13 — The operator screen is an output of the system, not a mock-up of it.** Every number, claim,
hash and log line a human sees comes from a row. No component holds a fixture, no API client answers
a failure with invented data, and a failed gate action is reported as a failure. Rules R3 and R4
apply to TypeScript exactly as they apply to Python — front-end code is where an invented fact meets
the only human who could have caught it. Added after defect V-03 (audit §15.4); enforced by Guard 8
in `tests/unit/test_no_fabrication.py`.
