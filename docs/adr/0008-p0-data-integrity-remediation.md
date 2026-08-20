# ADR-0008 — Data Integrity and Immutability Enforcement

**Status:** Accepted
**Date:** 2026-08-20
**Relates to:** ADR-0001, ADR-0002, ADR-0003, P0 Audit Findings

## Context

A recent schema audit (P0 findings A-01 through A-05) identified that database-level enforcement was missing for several critical invariants established in earlier ADRs:
- Enums (`ScopeMode`, `SourceTier`) were either unchecked or misaligned.
- The `Evidence -> Snapshot -> Source` traceability chain allowed an Evidence row to claim a Source but point to a Snapshot from a different Source.
- ADR-0003 defined knowledge as immutable, but the database lacked triggers or permissions to block `DELETE` or `UPDATE` operations on historical knowledge tables, and the application repositories performed overwrites.
- Local storage operations lacked path validation and atomicity.

## Decision

**Enforce invariants directly in the database using constraints and triggers, and secure local storage operations.**

1. **Schema alignment:** Align `Focus.scope_mode` and `Source.source_tier` CHECK constraints directly with the application enums via a new Alembic migration.
2. **Traceability chain constraint:** Add a `UNIQUE (id, source_id)` constraint on `snapshots`, and upgrade the `evidence` foreign key to be a composite `(snapshot_id, source_id)`. This guarantees that an evidence record cannot forge its source.
3. **Database-level immutability:** Add `BEFORE DELETE` triggers that universally reject row deletion on core knowledge tables (`topics`, `claims`, `domains`, `entities`, `channels`, `blackout_rules`, `sources`, `snapshots`, `evidence`, `knowledge_object_versions`, `claim_evidence`, `focus`).
4. **Append-only verification:** Add `BEFORE UPDATE` triggers to block modifications to strictly immutable records (`sources`, `snapshots`, `evidence`, `knowledge_object_versions`, `claim_evidence`, `focus`). Entities like `topics` and `claims` remain updatable for their state machine fields (`status`), but their history must be preserved via versioning or append-only structures in Phase 3.
5. **Secure Storage Adapter:** The `LocalStorage` adapter now enforces strict regex validation on the `storage_key` (`^sha256/[0-9a-f]{2}/[0-9a-f]{2}/[0-9a-f]{64}$`) to prevent path traversal, and uses atomic rename operations for writes.

## Consequences

- Direct `DELETE` queries on knowledge objects will throw a database exception, preventing accidental data loss or cascading deletes.
- The traceability chain is physically unbroken and provable at the schema level.
- Local storage is isolated and safe against traversal attacks.
- Attempting to overwrite historical versions will fail immediately rather than silently replacing data.
