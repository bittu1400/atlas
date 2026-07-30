# ADR-0003 — Knowledge versioning and storage shape

**Status:** Accepted
**Date:** 2026-07-30
**Relates to:** D10, D11, D13

## Context

`prompt.md` states that every revision is preserved and knowledge is never destroyed. Two questions
follow: how is history represented, and what shape does a Knowledge Object take in Postgres?

The constraints pull in different directions. The traceability chain — assertion → Claim → Evidence →
Source → Snapshot — must be enforceable by the database, because it is the one thing Atlas cannot get
wrong. Meanwhile the exploratory parts of a Knowledge Object (story angles, psychology notes, keywords,
platform metadata) will change shape repeatedly during the first year, and a migration per field change
would make iteration painful enough that the schema would rot instead.

There is also a requirement that is easy to miss: retraction. When a Claim is later found false, Atlas
must be able to answer which published artifacts used it.

## Decision

**Row-per-version with a `current` pointer, a typed core with a versioned JSONB payload, and a normalized
traceability chain.**

1. **Versioning.** Each revision of a Knowledge Object is a new row sharing a stable `ko_id`, with
   `version`, `created_at`, `actor_id`, and `reason`. A pointer identifies the current version. Nothing is
   updated in place; nothing is deleted.
2. **Applied as a shared capability, not a Knowledge Object feature.** Scripts, Storyboards, Assets, and
   Renders use the same pattern. `prompt.md` lists version history as a Knowledge Object field, but
   Scripts are revised far more often than knowledge is, and rejection-driven regeneration makes Script
   history the most valuable history Atlas keeps.
3. **Typed core, JSONB payload.** Stable, queryable, constrained columns for `ko_id`, `version`,
   `topic_id`, `entity_id`, `status`, `quality_score`, `confidence`, timestamps, and actor. Evolving
   fields live in a JSONB `payload` carrying `schema_version`, upcast on read by a chain of pure migration
   functions in the domain layer.
4. **The traceability chain is normalized with real foreign keys.** `claims`, `evidence`, `sources`, and
   `snapshots` are proper tables. Evidence references a Source and a Snapshot; a Claim's support is a
   foreign-key relationship, not a JSON array. A Claim with no Evidence is representable but is marked
   `unsupported` and excluded from Scripts by a database-checked constraint on publication paths.
5. **Snapshots are content-addressed.** Retrieved bytes are stored once by SHA-256, with retrieval
   timestamp and source URL. Citations resolve to a Snapshot, so they survive link rot.
6. **Impact index.** A `claim_usages` table records which Claim IDs appear in which Beats of which
   published Renders. Retraction becomes a query, and the corrections workflow becomes possible.
7. **Alembic** for migrations, autogenerate reviewed by hand.

## Alternatives considered

**Full event sourcing.** The most faithful representation of "knowledge is never destroyed," giving a
complete causal history of every mutation. Rejected because every read becomes a fold, every query
becomes a projection to maintain, and a single-operator platform would pay that complexity on every
feature forever. Row-per-version preserves everything that matters — the full content of every revision —
while remaining directly queryable.

**Audit or shadow tables only.** Cheap and conventional, but it makes history second-class: reconstructing
a past version means replaying audit rows, and the "current" table remains mutable, which is precisely
what the invariant forbids.

**All-JSONB documents.** Fastest to iterate and would have felt productive for a week. Rejected because
the traceability chain would then be enforced by application code alone, and the one invariant Atlas
cannot compromise would rest on nobody making a mistake. Foreign keys are not optional here.

**Fully normalized, no JSONB.** Maximum integrity, but a migration for every exploratory field. The
distinction that resolves this: fields the *system reasons about* get columns and constraints; fields the
system merely *carries* get JSONB.

## Consequences

- Any prior version of any versioned artifact is readable directly, which makes the dashboard's version
  diff view a straightforward query.
- The traceability invariant is enforced by the database, so a code bug cannot publish an unsourced claim.
- Storage grows monotonically. Approximately 500 MB per video including snapshots means a retention and
  archival policy is required before month six — noted as an open question in `docs/SPEC.md`.
- Payload upcasting must be pure, tested, and never lossy. Every `schema_version` bump needs an upcast
  function and a test proving old payloads still load.
- Reading the current version requires either the pointer or a `max(version)` predicate; indexes and a
  repository method make this uniform so no caller reinvents it.

## Trade-offs accepted

We give up event sourcing's complete causal record of *how* a revision came about, keeping only the
revisions themselves plus actor and reason. We accept unbounded storage growth in exchange for never
losing knowledge. And we accept that JSONB fields are not constrained by the database — mitigated by
Pydantic validation at every boundary, with the explicit rule that anything the system reasons about
must graduate to a typed column.

## Revisit when

- Payload upcasting exceeds roughly three chained schema versions, suggesting fields should graduate to
  columns.
- Storage growth becomes a real constraint and cold snapshots need archival.
- A field in JSONB needs to be queried or constrained — that is the signal to promote it, not to add a
  JSONB index and hope.
