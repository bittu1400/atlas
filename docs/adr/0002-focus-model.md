# ADR-0002 — The Focus model: scoping research by Field and Note

**Status:** Accepted
**Date:** 2026-07-30
**Relates to:** D14, D15, D16, D17

## Context

The operator wants two inputs: a **Field** selector (e.g. `Animal`) and a **Note** text box (e.g.
`tiger`). Having set them, the platform should work on tigers until told otherwise.

Read literally, that describes a global mutable setting. That reading is unworkable:

- It makes the pipeline non-reentrant. Three videos per day means concurrent Runs; a single global focus
  cannot serve them.
- Changing it mid-Run silently changes the meaning of work already in progress.
- It destroys traceability. A Run must be permanently answerable about the scope it was created under.
- It contradicts the explicit prohibition on hidden global state in `prompt.md`.

There is also a subtler opportunity in the two-input design that a naive implementation would waste.
`tiger` is ambiguous — an animal, a golfer, a tank, an operating system release. The Field resolves that
ambiguity. And the Field can carry far more than a category label.

## Decision

**A `Focus` is a first-class, versioned entity. Every Run captures its Focus by value at creation. An
`Active Focus` pointer supplies the default for newly created Runs.**

1. **Capture by value.** A Run stores its own immutable copy of the Focus it was created under. Changing
   the Active Focus never affects a Run in flight, and a Run from six months ago can still report exactly
   what scope produced it.
2. **Facets, not a fixed pair.** A Focus holds a list of typed `(dimension, value)` Facets. The UI shows
   exactly two inputs as requested; the model holds a list, so adding era, region, audience, or language
   later is configuration rather than redesign.
3. **Field is a policy selector, not a filter.** A Field maps to a **Domain** row carrying a **Research
   Profile**: source allowlists, preferred APIs, query-expansion vocabulary, disambiguation hints.
   `Animal` reaches for zoology and conservation databases; `History` reaches for archives and primary
   documents. This is what makes the second input earn its place.
4. **Note resolves to a canonical Entity.** At Focus creation the Note is resolved against Wikidata,
   scoped by the Domain, producing a QID. `Animal` + `tiger` → `Q19939`. Ambiguity is surfaced for
   operator confirmation, never guessed. Downstream, deduplication, graph traversal, and asset search key
   on the Entity rather than on a string.
5. **Scope Mode**, default `soft`. `hard` never leaves the Focus; `soft` prefers it while allowing
   adjacent graph nodes; `exploratory` treats it as a seed.
6. **Precedence** for new Runs: explicit arguments → Active Focus → Channel default.
7. **Auditable.** Focus creation and Active Focus changes are append-only records with actor and
   timestamp, consistent with how all Atlas state is treated.

## Alternatives considered

**A single global settings row.** What the request literally described. Rejected for the reentrancy,
traceability, and hidden-state reasons above. The Active Focus pointer delivers the same operator
experience — set it once, everything new follows — without any of the cost.

**Per-Run arguments only, no persistent default.** Clean and stateless, but it forces the operator to
retype the Field and Note for every Run, which is exactly the friction they asked to remove.

**Free-text Note with no Entity resolution.** Simpler and requires no external dependency. Rejected
because string matching cannot distinguish the tiger from the golfer, which means research pollution,
unreliable deduplication, and an asset search that returns golf photographs. The Field already contains
the information needed to disambiguate; not using it would be a waste.

**A hand-maintained internal taxonomy instead of Wikidata.** Full control, no external dependency, and
no upstream schema churn — but it means manually curating an ontology of everything Atlas might ever
cover. Wikidata is free, stable, license-clean, and already links to Wikimedia Commons, which is the
primary asset source. The Entity is stored as a local record with the QID attached, so a future switch or
a Wikidata outage degrades rather than breaks.

**Hard scope as the default.** Closest to the literal request. Rejected because a good 60-second video
about tigers legitimately needs lion comparison, poaching economics, and forestry policy. Hard mode
starves research on most topics within days. All three modes exist; only the default differs.

## Consequences

- Concurrent Runs on different Focuses work correctly with no special handling.
- Every Run is permanently traceable to the exact scope that produced it.
- Field becomes the natural place to encode source quality per subject area, which raises research
  quality without any additional operator effort.
- Entity anchoring makes "have we already covered this" a reliable query.
- Requires a Wikidata resolution adapter and a disambiguation confirmation surface in both the dashboard
  and the CLI.
- Domains and their Research Profiles must be seeded and maintained as data.

## Trade-offs accepted

Focus creation now involves a resolution step and, when ambiguous, a human confirmation — slightly more
friction than typing a word into a box. We accept it because the ambiguity would otherwise surface later
as polluted research, which costs far more to detect and repair. We also accept a dependency on an
external identifier scheme, mitigated by storing resolved Entities locally.

## Revisit when

- Facets grow past roughly six dimensions, at which point the UI needs rethinking rather than extending.
- Wikidata coverage proves inadequate for a Domain Atlas cares about, requiring a supplementary authority.
- Operators want multiple Active Focuses at once, e.g. one per Channel.
