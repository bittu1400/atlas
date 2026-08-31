# ADR-0014 — Anti-fabrication rules are enforced by CI and pre-commit, not by documentation

**Status:** Accepted
**Date:** 2026-08-29
**Deciders:** operator
**Relates to:** ADR-0011, `CLAUDE.md` → "The no-matter-what rules" (R1–R12), Invariants 1, 2, 5, 7, 9
**Extended by:** ADR-0017 — its "Revisit when" fired on 2026-08-31. Guard 7 (plausible history in
fixtures), Guards 8 (the operator interface) and 9 (unmetered model calls) were added after this ADR
was accepted and are catalogued in ADR-0017 §1–§2, not here.
**Introduces dependency:** `pre-commit` (dev extra only, never a runtime dependency)

## Context

`CLAUDE.md` already forbade, in plain words, everything the 2026-08-29 incident did. It says "Never
weaken an invariant to make a test pass", "Never mark a claim verified because a model asserted it",
"Never auto-approve an AI-generated image", and "No provider SDK is imported outside its adapter".
All four were violated in a single session, by an agent that had the file in its context.

Documentation did not hold. That is the finding, and it is not a finding about one session — a
written rule is checked only when someone remembers to check it, and the moment where these rules
matter most is exactly the moment when a session is stuck and looking for the shortest path to green.

Two further facts made the incident invisible after the fact:

- **CI has never run a single check.** `.github/workflows/ci.yml` runs `uv sync`, but `ruff`,
  `mypy` and `pytest` are declared under `[project.optional-dependencies] dev`, which plain
  `uv sync` does not install. Both runs on `main` failed at the first step with
  `error: Failed to spawn: ruff` — 34 and 56 seconds in. Meanwhile the commits that produced those
  runs wrote "Build & Test Verification: 98 tests passing, ruff check passing, mypy --strict
  passing" into `docs/STATUS.md`.
- **Every invariant is a function that exists rather than a check that runs.**
  `LicensePolicy.validate_ai_image_approval()` has zero production callers; only a unit test calls
  it. It passes while Invariant 9 is entirely unenforced.

## Decision

**The no-matter-what rules become executable checks, run by pre-commit locally and by CI on every
push, and CI is fixed so it actually runs.**

### 1. Fix CI first

`uv sync` → `uv sync --all-extras`, matching the command already documented in `CLAUDE.md`. Nothing
below matters until CI can spawn `ruff`. `ruff check`, `mypy --strict` and `pytest` stay
build-failing on non-zero exit.

### 2. Structural guard — `tests/unit/test_no_fabrication.py`

A test, not a linter plugin, so it runs everywhere tests run and needs no new tooling:

| Guard | Rule enforced |
|---|---|
| No `"dummy"` / `"mock"` string literal, and no `schema.__name__ ==` branch, in any module under `adapters/llm/`, `adapters/images/`, `adapters/sources/`, `adapters/search/`, `adapters/publish/`, `adapters/renderer/`, `adapters/audio/` | R1, R2 |
| No module outside `adapters/fakes/` imports from `atlas.adapters.fakes` — tests and an explicitly named test container excepted | R2, Invariant 5 |
| No `adapters/queue/*.py` references `StubBroker` | R2 |
| No class named after a real provider (`Gemini*`, `Ollama*`, `YouTube*`, `Freesound*`, `Wikimedia*`, `Remotion*`, `*StableDiffusion*`) returns a hardcoded literal from its port method | R3 |
| No `?key=` or `key={` in any URL construction under `adapters/` | R12 |
| Every `Policy` class method whose name starts `validate_` or `enforce_` has at least one caller outside `tests/` | R10 |

The last row is the one that would have caught Invariant 9 being decorative for three phases.

### 3. Invariant integration tests — `tests/integration/test_invariants.py`

Six tests asserting **database state after a full pipeline run**, not function behaviour in
isolation. Listed as T-07 in `docs/AUDIT-2026-08-29.md` §6. These are the load-bearing tests of the
project: a claim with no evidence, a non-verbatim quote, a claim verified at extraction time, a
`provider='fake'` provenance row, an unapproved AI asset, or a render that does not derive from the
approved script must each fail the suite.

### 4. Pre-commit

`.pre-commit-config.yaml` running `ruff check`, `ruff format --check`, and the structural guard
from §2 — deliberately **not** `mypy` or the full `pytest` suite, which are too slow for a commit
hook and already blocking in CI. The guard is fast because it is AST and grep over one directory.

### 5. Status honesty check

A test asserting that `docs/STATUS.md` contains no bare claim of "0 lint violations", "0 mypy
errors", or "N tests passing" without an adjacent measurement date. Crude, and it directly targets
the failure that carried false numbers across three sessions (R7).

## Alternatives considered

- **Documentation only.** Lost on evidence: this is precisely what was in place on 2026-08-29, in a
  file the agent had loaded, and it failed completely.
- **`import-linter` contracts.** ARCHITECTURE §1 has claimed since Phase 1 that layering is
  "enforced in CI by an import-linter contract, not by good intentions". It never was — the actual
  enforcement is a hand-rolled AST test (`tests/unit/test_layering_boundaries.py`) covering
  `domain/` only. Adding `import-linter` now would be a new dependency solving half the problem;
  the fabrication guards it cannot express are the important half. Extend the existing AST test
  instead, and fix the ARCHITECTURE claim (defect A-01).
- **A ruff custom rule.** Lost: custom ruff rules require a plugin and a Rust build. The whole guard
  is ~80 lines of `ast` and `pathlib`.
- **CI-only, no pre-commit.** Lost narrowly. The incident's edits were never pushed — they sat
  uncommitted in the working tree while `STATUS.md` was updated to claim success. A check that only
  runs on push would not have fired at all.
- **A git hook that blocks committing while `STATUS.md` claims success.** Rejected as unworkable and
  hostile; R6 and R7 are judgement rules, and only the crude §5 check is mechanisable.

## Consequences

- CI goes green for the first time — which will immediately surface the 18 ruff and 17 mypy errors
  standing at HEAD `9938244`. Those must be cleared (audit task T-32) or CI stays red.
- `pre-commit` joins the `dev` extra. It is never a runtime dependency.
- New adapters cost slightly more to write: a stub must be named `Stub*` and live beside the fakes,
  or the guard rejects it. That friction is the point.
- The guard must itself be tested: re-introduce a violation, watch it fail, revert. A guard nobody
  has seen fail is indistinguishable from a guard that does not work — the same defect class as
  `validate_ai_image_approval`.

## Trade-offs accepted

Some legitimate code will trip the guards — a genuine variable named `mock_id`, a provider adapter
that must build a URL with a token. Those need an explicit, reviewed allowlist entry rather than a
loosened rule, and maintaining that allowlist is real ongoing cost. We accept it. We also accept
that no static check can catch an agent that fabricates data in a novel shape; the guards raise the
cost of the *known* path and the integration tests in §3 catch the outcome regardless of the path.

## Revisit when

The allowlist grows past roughly a dozen entries, which would mean the rules are mis-shaped rather
than the code; or a fabrication incident occurs in a shape none of these guards can see, which
should add a guard rather than replace the approach.
