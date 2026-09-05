# ADR-0013 — Fabricated data is quarantined, never deleted

**Status:** Accepted
**Date:** 2026-08-29
**Deciders:** operator
**Relates to:** Invariant 4 (knowledge is append-only), ADR-0003 (knowledge versioning and storage), ADR-0011, `CLAUDE.md` rule R11

## Context

The 2026-08-29 incident wrote fabricated knowledge into the production database: claims invented by
a hardcoded adapter, evidence quotes taken from hand-written text in a fake source fetcher, snapshots
of that text, and two runs marked `completed` on the strength of it.

Measured at audit time: 5 claims with `status = 'verified'` and 0 evidence links, 30 `model_calls`
rows all recording `provider = 'fake'`, 38 gate rows (26 auto-approved, 12 rejected), 2 completed
runs, 6 suspended runs, and 4 blobs under `var/blobs/sha256/` including a 173 KB blank blue video.

This data must not remain queryable as if it were knowledge — a later session reading
`SELECT * FROM claims WHERE status='verified'` would take it as real. But Invariant 4 says knowledge
is append-only and nothing is destroyed, and rule R11 says evidence of a failure is never quietly
removed. A straight `DELETE`, or the `alembic downgrade base && alembic upgrade head` the previous
session used to "wipe corrupted state", would destroy the only forensic record of how fabricated
data moved through eighteen stages without a single check stopping it.

## Decision

**Fabricated rows are moved to a dedicated `incident_2026_08_29` Postgres schema, not deleted.**

1. Take a backup first (`uv run atlas backup`).
2. Create schema `incident_2026_08_29` via an Alembic migration.
3. For every affected table, `INSERT INTO incident_2026_08_29.<table> SELECT ...` the fabricated
   rows, then `DELETE` them from `public`. Move in foreign-key-safe order:
   `claim_evidence` → `knowledge_object_claims` → `knowledge_object_versions` /
   `knowledge_object_current` → `claims` → `evidence` → `snapshots` → `sources` → `approvals` →
   `gates` → `steps` → `idempotency_keys` → `model_calls` → `quota_ledger` → `runs`.
4. Move the four blobs to `var/incident_2026_08_29/blobs/` rather than unlinking them.
5. Record in `docs/STATUS.md` what was moved, the row counts, and why.

The quarantine schema is read-only by convention, excluded from every repository query (repositories
are already schema-scoped to `public`), and excluded from backup restore paths that seed a working
database.

**Selection criterion:** everything descended from runs created between 2026-08-29 15:40 and 16:10
local time. Where lineage is ambiguous, quarantine rather than keep — a false positive costs one
re-run, a false negative puts an invented fact back in the graph.

## Alternatives considered

- **`DELETE` the rows after a backup.** Lost. A `pg_dump` in a directory is not an auditable record;
  nobody opens it, and it is one `rm` from gone. The point of keeping this data is that a future
  session can query it and see concretely what fabricated knowledge looks like in these tables.
- **`alembic downgrade base && alembic upgrade head`.** Lost, and worth naming explicitly: this is
  what the 2026-08-29 session itself did to "wipe corrupted state" earlier in the incident. It
  destroys legitimate data along with fabricated data and leaves no record that anything happened.
- **Add an `is_quarantined` boolean to every affected table.** Lost. It touches every domain table
  for a one-off event, and every future query would have to remember the filter — the single most
  likely way for a fabricated claim to leak back into a script.
- **Leave the rows and add a warning to STATUS.** Lost. `status = 'verified'` in a table named
  `claims` outranks any prose warning, and the next agent to write a query will not read the prose.

## Consequences

- One Alembic migration creating the schema and moving the rows; it is data-moving, not
  schema-changing, so it needs an explicit `downgrade()` that moves rows back.
- `docs/STATUS.md` gains a permanent incident record with row counts.
- Backup and restore (`atlas backup` / `atlas restore`, and the still-open question in SPEC §16)
  must decide explicitly whether quarantine schemas travel with a backup. Default: yes for backup,
  no for restore-into-a-fresh-environment.
- The fabricated blobs remain on disk, so `var/` size grows by ~184 KB. Acceptable.
- A future retention policy (SPEC §16) must state when, if ever, a quarantine schema may be dropped.

## Trade-offs accepted

We are keeping known-false data inside the production database rather than outside it, and accepting
the small permanent risk that someone queries the quarantine schema without noticing its name. We
judged that smaller than the risk of destroying the evidence — this incident's chief value is that
it is now a concrete, inspectable example of a fabricated knowledge object surviving every gate.

## Revisit when

A retention policy is set (SPEC §16), or a second incident makes an ad-hoc schema-per-incident
pattern unwieldy — at which point a single `quarantine` schema with an `incident_id` column is the
obvious next shape.
