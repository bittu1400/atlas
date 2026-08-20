# GPT Audit — 2026-08-20

## Handoff verdict

**Do not begin Phase 3 yet.** The Phase 2 baseline is mechanically healthy but does not enforce several non-negotiable Atlas invariants. Remediate P0, add the listed regression/concurrency tests, and re-audit before Phase 3.

This is a fresh audit of the current working tree; it does not assume earlier reports remain correct. No application code was changed.

## Verification performed

- Reviewed STATUS, SPEC, ADRs, migrations, ORM mappings, repositories, domain models, storage adapter, and tests.
- `uv run ruff check .`, `uv run mypy .`, and `uv run pytest` all passed: 0 lint violations, 0 type errors across 52 source files, and 33 passed in 1.92 s.
- `0001_initial_schema.py` and the ORM each define **25 tables**, not the 26 reported in STATUS.

Passing tests cover the happy paths; they do not prove invariant enforcement or concurrent correctness.

## P0 — fix before Phase 3

### A-01 — ScopeMode schema mismatch

`ScopeMode` and ADR-0002 define `hard`, `soft`, and `exploratory`, but `FocusTable` and `0001` accept only `strict` and `soft`. Persisting a valid `HARD` or `EXPLORATORY` Focus fails. Align the CHECK to the enum in a **new migration** and test every mode.

### A-02 — SourceTier schema mismatch

`SourceTier` defines `primary`, `peer_reviewed`, `institutional`, `reference`, and `unvetted`, consistent with SPEC §9. The database CHECK instead permits `journalistic`, `expert_analysis`, and `speculative`, and rejects `reference`/`unvetted`. Valid sources fail to save, while invalid raw data creates read-time enum errors. Align the CHECK to the enum; test every valid value and unknown-value rejection.

### A-03 — Local storage path traversal / arbitrary local-file reads

`LocalStorage._sync_get()` and `_sync_exists()` use `root_path / storage_key` without validating the key. `../` escapes the root and an absolute key discards it. Future API/worker callers could read arbitrary files available to the Atlas process. Accept only the generated `sha256/<2hex>/<2hex>/<64hex>` format; reject absolute/traversal paths and verify resolved containment. Add tests. Use atomic writes (temp + replace) so concurrent readers never see partial content.

### A-04 — False traceability chain is database-permitted

`EvidenceTable` independently references a source and snapshot. No constraint proves that the snapshot belongs to that source, and `get_traceability_chain()` does not compare them. Evidence may cite Source A while its archived bytes are from Source B yet appear fully traceable. Add `UNIQUE (id, source_id)` on snapshots and a composite FK from evidence `(snapshot_id, source_id)`, or derive source solely through the snapshot. Add a direct database rejection test.

### A-05 — Append-only is not enforced

Repositories overwrite Topics, Claims, Domains, Entities, Channels, and BlackoutRules. ORM delete cascades and current schema permit deletion/change of historic non-current KO data and claim links. No trigger or restricted writer role blocks raw `UPDATE`/`DELETE`. This contradicts Invariant 4 and ADR-0003. Decide the precise immutable/versioned entities, use insert-only/superseding APIs, enforce immutability in DB permissions or triggers, and test rejected direct updates/deletes.

## P1 — repair in the Phase 2 remediation batch

### B-01 — Cross-run execution records are possible

`gates` separately FK `run_id` and `step_id`; approvals and model calls repeat a run ID independent of the referenced gate/step. Mismatched rows are accepted and corrupt the execution audit. Add composite keys/FKs (for example `steps(id, run_id)`), derive approval run from gate or constrain it, and test mismatches.

### B-02 — Approval double-resolution race

`record_approval()` checks a gate without a row lock and `approvals.gate_id` is non-unique. Two sessions can both see `pending`, insert opposing decisions, and last write wins. Lock the gate in the transaction and add unique `approvals.gate_id` defense in depth. Add a two-session test.

### B-03 — KO current pointer races/backward moves

`save_version()` accepts arbitrary versions and updates the current pointer without locking or enforcing next-version ordering. Late concurrent commits can regress v3 to v2. Lock/create pointer atomically, require `current + 1`, reject skips/stale writes with a typed error, and test concurrent writers.

### B-04 — Claimed step idempotency is not unique

`ix_steps_idempotency` is a non-unique index; duplicate `(run_id, step_name, input_hash)` steps can run. The idempotency key is an opaque caller string unrelated to its step, and expired keys are returned. Add a unique constraint, construct/validate key material internally, ignore expiry, and test duplicate/expired/concurrent retries.

### B-05 — First resource-lock acquisition races

`FOR UPDATE` cannot lock an absent `resource_locks` row. Two first acquisitions can both insert, giving one caller a raw `IntegrityError` instead of `ResourceLockHeldError`. Use an advisory transaction lock or atomic upsert with typed conflict handling; reject non-positive TTLs and test concurrent first acquisition.

### B-06 — Canonical entity/scoping integrity is incomplete

`wikidata_qid` is not unique, and Topic/Focus/KO entity/domain references are mostly unconstrained strings. This admits duplicate QIDs and orphan/mismatched scope bindings; canonical lookup can raise `MultipleResultsFound`. Add unique non-null QID and intended FKs/compatibility checks with tests.

### B-07 — Content-addressed snapshot metadata is not verified

`content_hash` is non-unique and `storage_key` is arbitrary, so duplicate or hash/key-mismatched snapshots can be saved. The acceptance test stores an S3-style key while the only adapter accepts local relative keys. Define backend-neutral key semantics, enforce/verify hash/key association, and test duplicate content/mismatch/retrieval.

## P2 — required hardening and documentation

- **C-01 Timezones:** domain fields accept naive datetimes; PostgreSQL interprets them by session zone; audience/operator helpers silently treat naive input as UTC. Reject naive values and normalize persisted times to UTC.
- **C-02 Schema validation parity:** critical numeric bounds, publishing day/rank/time intervals, and blackout interval validity lack DB checks. The DB also allows quota `month` while `WindowType` does not. Align and direct-SQL test constraints.
- **C-03 State machine:** Run/Step updates permit every enum transition and inconsistent terminal timestamps. This is Phase 3 work, but must not be represented as already durable.
- **C-04 KO lookup:** `get_current_for_topic()` uses `scalar_one_or_none()` even though multiple current KOs per Topic are legal. Enforce one or return/select explicitly.
- **C-05 Query shape:** `get_history()` has an N+1 claim-link query pattern; batch before history endpoints arrive.
- **C-06 Documentation:** README still says there is no runnable code and Phase 2 is next. STATUS table count was inaccurate. Corrected below.

## Recommended next-session order

1. Write failing regression tests for A-01–A-05, including direct DB writes.
2. Design a follow-up migration; do **not** rewrite an already-deployed `0001` migration. Record architecture-changing choices in ADRs.
3. Implement/verify P0, then B-01–B-05 with concurrent transaction tests.
4. Resolve entity/snapshot contracts, validation parity, docs, and run clean migration round trips plus full checks.
5. Update STATUS and only then start Phase 3.

## Phase boundary notes

Quota reservations/token buckets, transactional enqueue, workers/reaping, FastAPI, and actual publication paths are Phase 3+ scope. Asset/render persistence is later too. Before a render/publication path is built, it must call an enforced traceability and license gate: the current pure `validate_claim_publication_readiness()` helper is not connected to a persistence or publication boundary.
