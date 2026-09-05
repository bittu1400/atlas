# ADR-0017 — Anti-fabrication enforcement covers the operator interface and every model call site

**Status:** Accepted
**Date:** 2026-08-31
**Deciders:** operator
**Extends:** ADR-0014 (does not supersede it — every guard ADR-0014 introduced still stands)
**Relates to:** ADR-0004, `CLAUDE.md` → R3, R4, R5, R8, R13, Invariants 1, 7, 8
**Introduces dependency:** none

## Context

ADR-0014 made the no-matter-what rules executable, and its "Revisit when" says:

> a fabrication incident occurs in a shape none of these guards can see, which should add a guard
> rather than replace the approach.

That happened. On 2026-08-31 a second independent verification (audit §15) found that while the
Python side was clean — seven guards passing, 122 tests green, no fake importable from production
code — the **operator dashboard was a fabrication surface end to end**:

- Four components rendered hardcoded claims, invented citations and invented `sha256:` snapshot
  hashes, under a badge reading "Invariant 1 & 4 Enforced".
- The API client answered an unreachable backend with fabricated Runs, fabricated archival assets
  and a fabricated quality report scoring 84.5 with every deterministic check passing.
- A **failed** gate approval was reported to the operator as a recorded decision.
- A Remotion fixture of eleven beats of invented history was played in a panel labelled "rendering
  engine".
- `GET /events/runs/{run_id}` streamed two hardcoded SSE messages — `connected`, then
  `state: "active"` — for any run ID, without checking the run existed. Its own docstring said
  "mock/real SSE events".

Every guard ADR-0014 built parses Python under `packages/atlas/src/atlas/`. None of them can see a
`.tsx` file or an `apps/` route handler. And the surface they could not see is the **last one before
a human** — the place where an invented fact does its actual damage, because it is where a person
decides whether to approve a gate.

Two further gaps of the same shape were found at the same time:

- **Invariant 8 was decorative at two call sites.** `TopicDiscoveryAgent` (stage 1, every Run) and
  `StoryboardAgent` (two embeddings per Storyboard) reached a provider with no `QuotaManager` at
  all. This is precisely ADR-0014's own diagnosis — "every invariant is a function that exists
  rather than a check that runs" — applied to metering instead of licensing.
- **The production wiring had no test.** Of everything `Container` resolves, only `LocalStorage` was
  touched by any test, and `Container` itself was never constructed in one. That is why
  `LoggingNotifier` shipped raising `TypeError` on every gate suspension while the suite was green.

## Decision

**The anti-fabrication guards extend to the operator interface and to every model call site, and the
production container gets a test that constructs it.**

### 1. Guard 8 — the operator UI invents nothing (R4, R13)

Four checks in `tests/unit/test_no_fabrication.py`, over every hand-written `.ts` and `.tsx` file in
`apps/web/src/` and `apps/renderer/src/`, with `//` comment lines stripped so a guard does not fire
on its own explanation:

| Check | Rule enforced |
|---|---|
| No sentence matching Guard 7's plausible-history patterns — century references, dated claims, named polities, attestation language | R4, R13 |
| No hardcoded `sha256:` literal; a provenance hash on screen is a database row | R4, R13 |
| `api/client.ts` contains no `MOCK_API` switch and no `catch` — a failed request fails | R4, R8, R13 |
| `ApprovalQueue.tsx` contains no "Simulated" / "simulation mode" / "dev mode" — a failed gate action is never displayed as a decision | R5, R8, R13 |

The last two are string checks on specific files rather than general structural rules. That is
deliberate and it is a known weakness: they name the exact regression rather than the class. They are
cheap, they name the defect in their own failure message, and a general rule here would need a
TypeScript AST parser in a Python test suite — see *Alternatives*.

### 2. Guard 9 — no model call escapes the ledger (Invariant 8)

An AST check over `application/agents/`: any class whose name ends `Agent` and which calls
`extract`, `embed`, `embed_batch` or `generate` on `self.llm` or `self.embedder` must also reference
`record_invocation`. An agent that can reach a provider must be able to meter it.

### 3. Rule R13 in `CLAUDE.md`

> The operator screen is an output of the system, not a mock-up of it.

Guards 8's four checks are its executable half. The rule exists because the guard cannot express the
whole of it — a component can invent data in a shape no regex matches.

### 4. The production container is constructed by a test

`tests/integration/test_production_adapters.py` builds `Container`, asserts no port resolves to a
module under `adapters/fakes/`, and exercises the six adapters that need no network. The
network-backed seven stay uncovered until cassettes exist (ARCHITECTURE §9, task T-36) and
`docs/STATUS.md` §3 says so rather than leaving it implied.

### 5. Fabricated endpoints are deleted, not labelled

`GET /events/runs/{run_id}` is removed. It had no consumer, and a stub route that answers with
plausible state is R3 in HTTP form. Real server-push returns when the dashboard needs it; today it
polls every five seconds through react-query, which is adequate at this scale (task **T-56**).

## Alternatives considered

- **A TypeScript AST guard (`ts-morph`, `typescript-estree`).** Lost on dependency cost: it means a
  Node toolchain inside the Python test suite, or a second test runner that CI must also run and
  that nothing else needs. The regex guard catches the shape that actually occurred, and the review
  rule R13 covers the rest. **Revisit if** Guard 8 misses a second incident.
- **ESLint rules in the web package.** Lost narrowly, and for a specific reason: the suite must run
  as one command. Splitting enforcement across two runners is how the front end came to have no
  enforcement at all — every existing guard lived where the Python developer was looking.
- **A browser test asserting rendered output instead of a source guard.** Not an alternative — it is
  the *better* check and it is missing. Guard 8 proves the sources hold no fixture; nothing proves
  the screen renders what the API returned. Recorded as an open item in `STATUS.md` §3 and
  ARCHITECTURE §11.8 rather than pretended away. **This is the most valuable single thing the next
  session could add.**
- **Labelling the fabricated panels "SAMPLE DATA" and keeping them.** Rejected. A banner is one
  glance away from being missed, and the panels were showing provenance — hashes, sources, evidence
  counts — which is the one category of data whose whole value is that it is not decorative.
- **Making `/events` a real SSE stream now.** Rejected as scope: it needs a pub/sub or a polling
  bridge, and the dashboard has no requirement the 5-second poll does not meet.

## Consequences

- Front-end changes now have a failing check to satisfy, in a suite front-end work did not
  previously run. `uv run pytest` is the gate for `apps/web` as well as for Python.
- Guard 8's file-specific checks will need editing if `ApprovalQueue.tsx` or `client.ts` is renamed.
  Accepted: the alternative is a general rule that needs a parser.
- Adding an agent now costs a `QuotaManager` constructor argument. That friction is the point,
  exactly as ADR-0014 said of stub naming.
- `Embedder` gained `provider` and `model_id` so an embedding's `model_calls` row can name the
  adapter that ran (Invariant 7). Any future `Embedder` implementation must supply both.
- One fewer route on the API surface, and the SSE JSON-injection test goes with it — the property it
  protected cannot be violated by an endpoint that does not exist.

## Trade-offs accepted

Guard 8 is coarser than Guard 7: it scans file text rather than parsing an AST, so a fact split
across a template literal or assembled at runtime slips through. It also cannot see anything the
browser composes. We accept that, because the incident it targets was blunt — literal arrays of
invented claims in component bodies — and because the honest fix for the residue is a browser test,
which is recorded as open rather than substituted for.

## Revisit when

A browser test exists, at which point Guard 8's file-specific checks (rows 3 and 4) can be replaced
by assertions about what the screen actually renders; or a front-end fabrication occurs in a shape
the text scan cannot see, which should add a check rather than replace the approach.
