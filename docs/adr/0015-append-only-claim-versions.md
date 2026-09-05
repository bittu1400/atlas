# ADR-0015 — Claim state is append-only: identity row plus `claim_versions`

**Status:** Accepted
**Date:** 2026-08-31
**Deciders:** operator
**Relates to:** Invariant 4, ADR-0003 (knowledge versioning), D88, D89, defect B6
**Migration:** `b1c4d7e90a25_append_only_claims_and_production_artifacts`

## Context

Invariant 4 says knowledge is append-only: "Nothing is ever destroyed or edited in place. New
version, new row, old row intact, provenance recorded." Knowledge Objects have obeyed this since
ADR-0003 — `knowledge_object_versions` is row-per-version with a separate current pointer.

Claims did not. `SourceRepository.save_claim` was an upsert:

```python
existing = await self.session.get(ClaimTable, claim.id)
if existing:
    existing.text = claim.text
    existing.status = claim.status.value
    ...
```

Every `unverified → verified` transition overwrote the row that recorded the previous state. There
was no record of who changed it or why. Since a Claim's status is exactly the fact that decides
whether an assertion may reach an output, this is the single most consequential value in the system
and it had no history. The audit register had not caught it; it was found on 2026-08-31 by reading
the write path.

## Decision

`claims` becomes an immutable identity row — `id` and `created_at`, nothing else. Every mutable
field moves to a new append-only table:

```
claims         (id, created_at)
claim_versions (claim_id, version, text, assertion_type, confidence, status,
                inferred_from_claim_ids, actor_id, reason, created_at)
```

`(claim_id, version)` is the primary key. The current state of a Claim is its highest-numbered
version. `save_claim(claim, actor_id, reason)` inserts the next version and never updates; both
arguments are required, so a state change cannot be written anonymously. `get_claim_history`
returns every version oldest-first.

The `Claim` domain model gains a `version: int` field so callers can see which revision they hold.

## Alternatives considered

- **An audit-log table beside a still-mutable `claims` row.** Smaller diff: no read path changes,
  no backfill. Rejected because the row of record would still be edited in place, which is the
  literal thing Invariant 4 forbids; the history would be a courtesy copy that nothing reads, and
  a bug that skipped the log would be undetectable.
- **A new Claim row with a new ID per revision, linked by `supersedes_claim_id`.** Rejected because
  `claim_evidence`, `knowledge_object_claims` and `claim_usages` all key on `claims.id`. Changing
  the ID on every status transition would either break those foreign keys or require rewriting them
  on each change — which is itself an in-place edit.
- **Leaving it alone and documenting the gap.** Rejected: Invariant 4 is not conditional, and the
  repair gets more expensive with every claim written.

## Consequences

- "Who marked this claim verified, and on what grounds" is answerable by query, for every claim.
- Reads cost one extra lookup (`ORDER BY version DESC LIMIT 1`), covered by
  `ix_claim_versions_claim_version`.
- Every `save_claim` call site must name an actor and a reason. Agents supply
  `agent.extraction` / `agent.verification`; tests supply an explicit fixture reason.
- Raw SQL against `claims.status` or `claims.text` no longer works; it must go through
  `claim_versions`. Two tests were updated accordingly.
- The migration backfills existing rows as version 1 with actor `migration.b1c4d7e90a25`, so no
  history is invented and none is destroyed (rule R11).

## Trade-offs accepted

- `claim_versions` grows without bound. There is no compaction and none is planned; at Atlas's
  volumes a claim will have single-digit versions.
- Reading the current state of N claims is N queries through the repository. If that becomes hot,
  the fix is a batched "latest version per claim" query, not a denormalised status column on
  `claims` — a cached current-state column would reintroduce exactly the in-place write this ADR
  removes.

## Revisit when

Claim history is queried often enough that the per-claim latest-version lookup shows up in a
profile, or a retraction workflow needs to branch history rather than append to it.
