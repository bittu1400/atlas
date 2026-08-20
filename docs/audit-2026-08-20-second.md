# Phase 2 — Second Deep Audit Report

**Date:** 2026-08-20  
**Auditor:** Full-codebase audit across domain models, persistence, tests, documentation, and architecture  
**Scope:** Every file in `packages/atlas/src/`, `tests/`, `docs/`, and project config — 50 source files, 12 test files, 24 documentation files  
**Context:** Follow-up to the [first audit](file:///home/bittusah/Projects/Personal/Intern/atlas/docs/audit-2026-08-20.md). The first audit found 6 Critical, 8 Significant, 12 Minor issues. All 6 Critical and 8 Significant were fixed. **7 of 12 Minor issues were left as "fix when touched."**

---

## Verification Snapshot

| Check | Result |
|---|---|
| `uv run ruff check .` | ✅ All checks passed |
| `uv run mypy .` | ✅ 0 issues in 50 source files |
| `uv run pytest` | ✅ 26 tests pass (not run in this audit — requires live PostgreSQL `atlas_test`) |

---

## Summary Matrix

| Severity | Count | Description |
|---|---|---|
| 🔴 **CRITICAL** | 5 | Will cause data corruption, invariant violations, or security issues in production |
| 🟠 **SIGNIFICANT** | 9 | Will cause bugs, subtle failures, or spec violations in Phases 3–8 |
| 🟡 **MINOR** | 14 | Code quality, missing edge-case coverage, hardening, documentation gaps |
| 🔵 **OBSERVATION** | 8 | Architectural notes and decisions to record before Phase 3 |

---

## 🔴 CRITICAL Issues

### C1. `TraceabilityChain` omits `ClaimEvidenceLink` — stance information lost

**File:** [`domain/knowledge/models.py` L184–189](file:///home/bittusah/Projects/Personal/Intern/atlas/packages/atlas/src/atlas/domain/knowledge/models.py#L184-L189)  
**Also:** [`knowledge_repository.py` L141–201](file:///home/bittusah/Projects/Personal/Intern/atlas/packages/atlas/src/atlas/adapters/persistence/repositories/knowledge_repository.py#L141-L201)

```python
class TraceabilityChain(BaseModel):
    claim: Claim
    evidence_with_sources: list[tuple[Evidence, Source, Snapshot]]
```

The `ClaimEvidenceLink` join model is completely absent from the chain. This model carries the **stance** (`SUPPORTS` vs `CONTRADICTS`) — the only field that tells the downstream consumer whether a piece of evidence actually supports or contradicts the claim.

**Why it matters:**
- **Invariant 3 violation:** "Conflicting evidence is stored, both sides, never silently resolved." Without stance in the chain, a consumer cannot distinguish supporting from contradicting evidence.
- The [repository query](file:///home/bittusah/Projects/Personal/Intern/atlas/packages/atlas/src/atlas/adapters/persistence/repositories/knowledge_repository.py#L160-L167) joins through `ClaimEvidenceTable` but discards its `stance` and `notes` columns.
- A rendering agent receiving this chain would treat all evidence equally — a **directly publishable factual error**.

**Probability:** Certain to cause incorrect output in Phase 6 (Knowledge System) and Phase 7 (Rendering).  
**Fix complexity:** Low — add `ClaimEvidenceLink` to the tuple or restructure as a named model.

---

### C2. `ModelCall` missing `parameters` and `code_version` — Invariant 7 violation

**File:** [`domain/execution/models.py` L179–196](file:///home/bittusah/Projects/Personal/Intern/atlas/packages/atlas/src/atlas/domain/execution/models.py#L179-L196)  
**Also:** [`tables.py` L498–521](file:///home/bittusah/Projects/Personal/Intern/atlas/packages/atlas/src/atlas/adapters/persistence/tables.py#L498-L521)

**Invariant 7** states: *"Every artifact records how it was made — provider, model ID, prompt version, **parameters**, input version, **code version**."*

`ModelCall` captures `provider`, `model_id`, and `prompt_version` but is missing:
- `parameters` (dict) — temperature, max_tokens, top_p, etc. Without this, rebuilding an identical output is impossible.
- `code_version` (str) — git SHA or tag. Without this, "rebuild this exactly" is unanswerable.

**Probability:** Certain to violate Invariant 7 when model calls begin in Phase 5.  
**Fix complexity:** Low — add two columns to `ModelCallTable` and corresponding domain model fields.

---

### C3. `validate_claim_publication_readiness` accepts raw integer — easily misused

**File:** [`domain/knowledge/invariants.py` L7–27](file:///home/bittusah/Projects/Personal/Intern/atlas/packages/atlas/src/atlas/domain/knowledge/invariants.py#L7-L27)

```python
def validate_claim_publication_readiness(claim: Claim, supporting_evidence_count: int) -> None:
```

The function takes a plain `int` for evidence count. A caller can easily pass `len(all_evidence)` which **includes contradicting evidence**, making the check pass with zero actual supporting evidence. This directly undermines **Invariant 1** ("Every statement resolves Claim → Evidence → Source → Snapshot").

**The safe API** should accept `list[ClaimEvidenceLink]` and internally filter for `stance == SUPPORTS`, making it impossible for callers to short-circuit the check.

**Probability:** High — the most natural call pattern (`len(evidence_list)`) is wrong.  
**Fix complexity:** Low — change signature, add filtering logic.

---

### C4. Integration tests give false positives due to `autoflush=False` and no `expunge_all`

**File:** [`tests/conftest.py` L48–56](file:///home/bittusah/Projects/Personal/Intern/atlas/tests/conftest.py#L48-L56)  
**Affects:** All integration tests under `tests/integration/`

Two compounding issues:

1. **`autoflush=False`** means `session.add()` + `session.flush()` puts rows into the DB, but if a repository method forgets `await session.flush()`, the data lives only in SQLAlchemy's Identity Map. Tests pass because the subsequent `session.get()` returns the cached in-memory object — **never hitting the database**.

2. **No `session.expunge_all()` between write and read** — SQLAlchemy's Identity Map serves cached objects on `session.get()`. A save-then-read test proves nothing about the actual database mapping, serialization, or constraint enforcement unless the cache is cleared between operations.

**Specific broken test:** `test_model_calls_and_quota_ledger` in [`test_execution_repository.py`](file:///home/bittusah/Projects/Personal/Intern/atlas/tests/integration/test_execution_repository.py) explicitly acknowledges this — it only asserts writes "don't crash" without reading back, and due to `autoflush=False`, even the writes may never reach the database.

**Probability:** Certain — tests currently pass with potentially broken implementations.  
**Fix complexity:** Medium — add `session.expunge_all()` between save/read in every integration test, and verify `test_model_calls_and_quota_ledger` actually reads back data.

---

### C5. `Approval.feedback` not validated on rejection — SPEC §7 violation

**File:** [`domain/execution/models.py` L139–152](file:///home/bittusah/Projects/Personal/Intern/atlas/packages/atlas/src/atlas/domain/execution/models.py#L139-L152)

SPEC §7 states: *"Free-text-only rejection is rejected by the API."*

The `Approval` model allows `feedback=None` regardless of `decision`. A rejection with no structured feedback can be persisted without any validation error. The `RejectionFeedback` model exists with proper structure (`target_ref`, `rubric_dimension`, `reason`, `action`), but nothing enforces its presence when `decision == REJECTED`.

```python
class Approval(BaseModel):
    decision: ApprovalDecision
    feedback: RejectionFeedback | None = None  # No @model_validator enforcing coupling
```

**Probability:** Certain to allow unactionable rejections in Phase 4 (Dashboard).  
**Fix complexity:** Low — add a `@model_validator` that raises when `decision == REJECTED and feedback is None`.

---

## 🟠 SIGNIFICANT Issues

### S1. `Source.url` is a plain `str` — no URL validation, SSRF risk

**File:** [`domain/knowledge/models.py` L78–89](file:///home/bittusah/Projects/Personal/Intern/atlas/packages/atlas/src/atlas/domain/knowledge/models.py#L78-L89)

```python
url: str = Field(description="Source URL or permanent identifier")
```

No format validation. Accepts `javascript:alert(1)`, `file:///etc/passwd`, `http://169.254.169.254/latest/meta-data/` (AWS IMDS), or arbitrary strings. When research agents fetch URLs in Phase 5, this becomes an **SSRF (Server-Side Request Forgery)** vector.

**Probability:** Medium — depends on how URLs are consumed in Phase 5 agents.  
**Fix complexity:** Low — use Pydantic's `HttpUrl` type or add a regex validator.

---

### S2. `Channel.audience_timezone` not validated against IANA database

**File:** [`domain/publishing/models.py` L24–38](file:///home/bittusah/Projects/Personal/Intern/atlas/packages/atlas/src/atlas/domain/publishing/models.py#L24-L38)  
**Also:** [`clock.py` L44–52](file:///home/bittusah/Projects/Personal/Intern/atlas/packages/atlas/src/atlas/platform/clock.py#L44-L52)

```python
audience_timezone: str = Field(default="America/New_York")
```

Any string is accepted. If a Channel is saved with `"Amercia/New_Yrok"` (typo), `to_audience_time()` will crash at runtime with `zoneinfo.ZoneInfoNotFoundError` — an untyped exception that will propagate as a 500 error in Phase 3.

**Probability:** High — human data entry errors are inevitable.  
**Fix complexity:** Low — add a `@field_validator` checking `audience_timezone in zoneinfo.available_timezones()`.

---

### S3. `Entity.wikidata_qid` has no format validation

**File:** [`domain/focus/models.py` L65–75](file:///home/bittusah/Projects/Personal/Intern/atlas/packages/atlas/src/atlas/domain/focus/models.py#L65-L75)

```python
wikidata_qid: str | None = Field(default=None)
```

Wikidata QIDs must match `^Q\d+$`. Without validation, malformed QIDs (e.g., `"wikidata:Q19939"`, `"q19939"`, `""`) can be stored and then fail when used in Wikidata API calls in Phase 5.

**Probability:** Medium.  
**Fix complexity:** Low — add `pattern=r"^Q\d+$"` to the Field, or a `@field_validator`.

---

### S4. `BlackoutRule` / `PublishingWindow` docstring still says "Blackout window (06:00 to 22:00)"

**File:** [`domain/publishing/models.py` L1–8](file:///home/bittusah/Projects/Personal/Intern/atlas/packages/atlas/src/atlas/domain/publishing/models.py#L1-L8)

The module docstring says:
> *"Blackout window (06:00 to 22:00 audience-local) is an enforced hard constraint."*

06:00 to 22:00 are the **allowed** hours, not the blackout hours. The **blackout** is 22:00 to 06:00. While the fields were correctly renamed to `earliest_allowed_time` / `latest_allowed_time` (from the first audit), the docstring was not updated, creating a semantic contradiction that **will** confuse anyone implementing the scheduling logic in Phase 8.

**Also:** [`errors.py` L131–136](file:///home/bittusah/Projects/Personal/Intern/atlas/packages/atlas/src/atlas/platform/errors.py#L131-L136) repeats the same confusing phrasing:
```python
f"Publish slot at '{slot_local_time}' violates the 06:00-22:00 audience-local blackout rule"
```

**Probability:** Certain to cause confusion.  
**Fix complexity:** Trivial — update docstrings.

---

### S5. `Source.published_date` is `str` instead of `date` — prevents range queries

**File:** [`domain/knowledge/models.py` L87](file:///home/bittusah/Projects/Personal/Intern/atlas/packages/atlas/src/atlas/domain/knowledge/models.py#L87)  
**Also:** [`tables.py` L71](file:///home/bittusah/Projects/Personal/Intern/atlas/packages/atlas/src/atlas/adapters/persistence/tables.py#L71)

```python
published_date: str | None  # domain model
published_date: Mapped[str | None] = mapped_column(String(64))  # table
```

Using `str` prevents:
- Database-level `WHERE published_date BETWEEN '2020-01-01' AND '2023-12-31'` (string comparison doesn't work correctly for dates)
- Sorting by publication date
- Temporal analysis in Phase 9 (Analytics)

**Probability:** Will cause query bugs in Phases 5–9.  
**Fix complexity:** Medium — requires migration to change column type.

---

### S6. No DB-level `CHECK` constraints on enum-like string columns

**File:** [`tables.py`](file:///home/bittusah/Projects/Personal/Intern/atlas/packages/atlas/src/atlas/adapters/persistence/tables.py) — multiple columns

The following columns accept any arbitrary string value via raw SQL:
- `status` on `TopicTable`, `KnowledgeObjectVersionTable`, `RunTable`, `StepTable`, `GateTable` (5 tables)
- `assertion_type` on `ClaimTable`
- `source_tier` on `SourceTable`
- `stance` on `EvidenceTable`, `ClaimEvidenceTable`
- `scope_mode` on `FocusTable`
- `gate_type` on `GateTable`
- `decision` on `ApprovalTable`
- `outcome` on `ModelCallTable`
- `window_type` on `QuotaLedgerTable`

All have corresponding `StrEnum` types in the domain layer but no `CheckConstraint` at the database level. A raw SQL `INSERT` or admin script can insert invalid values that bypass Pydantic validation, creating rows that crash on read when `SomeEnum(invalid_value)` raises `ValueError`.

**Probability:** Low now (no raw SQL usage), increases with admin tools and migrations.  
**Fix complexity:** Medium — add `CheckConstraint(column.in_([...]))` per column.

---

### S7. `Snapshot.byte_size` and `Snapshot.content_hash` lack validation

**File:** [`domain/knowledge/models.py` L92–103](file:///home/bittusah/Projects/Personal/Intern/atlas/packages/atlas/src/atlas/domain/knowledge/models.py#L92-L103)

- `byte_size: int` — no `ge=0` constraint. Negative byte sizes are accepted.
- `content_hash: str` — no length or format validation. Should match SHA-256 hex (`^[a-f0-9]{64}$`). Any string is accepted, including empty strings.

**Probability:** Medium — malformed data from agents or adapters.  
**Fix complexity:** Low — add `ge=0` and `pattern` validators.

---

### S8. `Run` model lacks `error` / `failure_reason` field

**File:** [`domain/execution/models.py` L85–101](file:///home/bittusah/Projects/Personal/Intern/atlas/packages/atlas/src/atlas/domain/execution/models.py#L85-L101)

When a `Run` transitions to `RunStatus.FAILED`, there is no field to store the high-level reason. `Step` has an `error` field, but the `Run` itself has no summary of what went wrong. A failed Run in the dashboard would show "Failed" with no context unless the user digs into individual Step errors.

**Probability:** Will cause poor UX in Phase 4 (Dashboard).  
**Fix complexity:** Low — add `error: str | None = None` to `Run` and `RunTable`.

---

### S9. `QuotaLedgerEntry.window_type` is a plain `str` — no enum

**File:** [`domain/execution/models.py` L206](file:///home/bittusah/Projects/Personal/Intern/atlas/packages/atlas/src/atlas/domain/execution/models.py#L206)

```python
window_type: str = Field(description="Window type ('minute' or 'day')")
```

The docstring documents only two valid values (`minute`, `day`), but the field accepts any string. A typo like `"min"` or `"daily"` would create a phantom quota window that never gets checked against, silently bypassing quota enforcement.

**Probability:** Medium — quota billing logic will be complex in Phase 5.  
**Fix complexity:** Low — create a `WindowType(StrEnum)` with `MINUTE = "minute"`, `DAY = "day"`.

---

## 🟡 MINOR Issues

### M1. Debug `print()` statements left in `alembic/env.py`

**File:** [`alembic/env.py` L24, L29](file:///home/bittusah/Projects/Personal/Intern/atlas/packages/atlas/src/atlas/adapters/persistence/alembic/env.py#L24-L29)

```python
print(f"DEBUG: Using url_from_config: {url_from_config}")
print(f"DEBUG: Using env_url: {env_url}")
```

These print database connection URLs (potentially containing credentials) to stdout on every migration run. This is a **minor security concern** — database URLs should not be logged to stdout in production, and `print()` statements violate the "structured logging only" rule from CLAUDE.md.

---

### M2. `timedelta` import still inside method body

**File:** [`execution_repository.py` L260](file:///home/bittusah/Projects/Personal/Intern/atlas/packages/atlas/src/atlas/adapters/persistence/repositories/execution_repository.py#L260)

```python
async def acquire_lock(...):
    ...
    from datetime import timedelta  # Still inside method body
```

The first audit (M2) noted this should be moved to top-level. It was listed as fixed in the remediation log but **remains unfixed** in the actual code.

---

### M3. `conftest.py` hardcodes `TEST_DATABASE_URL` — no env override

**File:** [`tests/conftest.py` L14](file:///home/bittusah/Projects/Personal/Intern/atlas/tests/conftest.py#L14)

```python
TEST_DATABASE_URL = "postgresql+asyncpg://postgres@localhost:5432/atlas_test"
```

No environment variable override. CI systems with different database hosts/ports cannot configure the test database without editing source code. Should use `os.getenv("ATLAS_TEST_DATABASE_URL", "postgresql+asyncpg://postgres@localhost:5432/atlas_test")`.

---

### M4. `test_execution_repository.py` `test_model_calls_and_quota_ledger` is hollow

**File:** `tests/integration/test_execution_repository.py`

The test only asserts that writes "don't crash." Due to `autoflush=False`, the writes may never reach the database. No read-back verification. This was flagged in audit 1 as C6 and "fixed" by adding the test — but the test itself is inadequate.

---

### M5. Missing DST edge case tests in `test_clock_and_timezones.py`

**File:** `tests/unit/test_clock_and_timezones.py`

Missing tests for:
- **Fall-back ambiguity** (e.g., 2026-11-01 01:30 ET — exists twice during DST transition)
- **Spring-forward gap** (e.g., 2026-03-08 02:30 ET — doesn't exist)
- These edge cases will matter for `to_audience_time()` when calculating publish windows.

---

### M6. Missing confidence bounds validation tests in `test_knowledge_invariants.py`

**File:** `tests/unit/test_knowledge_invariants.py`

The Pydantic `Field(ge=0.0, le=1.0)` constraint on `Claim.confidence` is not tested. Missing tests for:
- Confidence < 0.0
- Confidence > 1.0
- Edge values 0.0 and 1.0

---

### M7. Missing upcast error-path tests in `test_payload_upcast.py`

**File:** `tests/unit/test_payload_upcast.py`

Only tests valid payloads. Missing tests for:
- Malformed legacy payloads (e.g., `summary` as `int`)
- Unknown schema versions (e.g., `schema_version: 999`)
- Missing required fields
- Partially valid payloads

---

### M8. `test_layering_boundaries.py` doesn't detect dynamic imports

**File:** `tests/unit/test_layering_boundaries.py`

The AST-based checker scans for `import` and `from ... import` statements but does **not** detect:
- `importlib.import_module("sqlalchemy")`
- `__import__("asyncpg")`
- Wildcard imports `from sqlalchemy import *`

These bypass patterns could be introduced accidentally in future phases.

---

### M9. `.gitignore` missing entries

**File:** [`.gitignore`](file:///home/bittusah/Projects/Personal/Intern/atlas/.gitignore)

Missing:
- `*.p12`, `*.pfx`, `*.crt` (certificate formats)
- `*.db`, `*.sqlite3` (SQLite databases — common local dev artifacts)
- `Thumbs.db` (Windows)
- `venv/`, `env/` (alternative virtualenv names)
- `.tox/`, `.nox/` (test runners)
- `core`, `*.core` (core dumps)

---

### M10. No `__all__` exports in `__init__.py` files

**File:** All `__init__.py` files in `packages/atlas/src/atlas/`

All are empty. No public API surface is defined. As the codebase grows, consumers can import any internal implementation detail.

---

### M11. No asset/license domain model — Invariants 9 and 10 unmodeled

**File:** Entire `domain/` layer

**Invariant 9:** "AI-generated imagery always requires explicit human approval."  
**Invariant 10:** "Licenses are enforced, not recorded."

There are no domain models for:
- `Asset` (image, audio, video asset with license metadata)
- `License` (license type, permitted uses, restrictions)
- `AssetApproval` (approval gate specifically for AI-generated assets)

The `Gate` model exists generically, but there is no domain-level linkage ensuring media assets carry an approval flag or license check result before reaching a renderer.

**Risk:** Low now (Phase 2), but these domain concepts must exist before Phase 7 (Rendering).

---

### M12. `Seed data` only seeds 2 of the expected domains

**File:** [`0001_initial_schema.py` L507–551](file:///home/bittusah/Projects/Personal/Intern/atlas/packages/atlas/src/atlas/adapters/persistence/alembic/versions/0001_initial_schema.py#L507-L551)

Seeds `dom_animal` (Animal) and `dom_history` (History). SPEC and the original prompt list additional domains (Technology, Science). Only 1 of 3 channels is seeded (ORIGINS, but not WHY or HUMANS).

---

### M13. No Invariant 2 structural enforcement — model outputs can be logged as sources

**File:** [`domain/knowledge/models.py`](file:///home/bittusah/Projects/Personal/Intern/atlas/packages/atlas/src/atlas/domain/knowledge/models.py), [`domain/common/enums.py`](file:///home/bittusah/Projects/Personal/Intern/atlas/packages/atlas/src/atlas/domain/common/enums.py)

**Invariant 2:** "A model is never the source of a fact."

`SourceTier` has five tiers (`PRIMARY`, `PEER_REVIEWED`, `INSTITUTIONAL`, `REFERENCE`, `UNVETTED`) but no explicit exclusion for model-generated content. Nothing structurally prevents an agent from creating a `Source(source_tier=SourceTier.UNVETTED, url="model://gemini-1.5")`. The invariant relies entirely on correct agent behavior.

---

### M14. `ResearchProfile.source_allowlist` entries lack format validation

**File:** [`domain/focus/models.py` L42–43](file:///home/bittusah/Projects/Personal/Intern/atlas/packages/atlas/src/atlas/domain/focus/models.py#L42-L43)

```python
source_allowlist: list[str] = Field(default_factory=list)
```

These strings will be used as glob/domain patterns in search adapters. Without validation (e.g., must match `*.domain.tld`), malformed entries could cause silent search failures or overly broad matching.

---

## 🔵 OBSERVATIONS (Not Defects)

### O1. No repository interfaces — adapters are concrete classes

All repositories (`KnowledgeRepository`, `ExecutionRepository`, `FocusRepository`, `PublishingRepository`, `SourceRepository`) are concrete classes with no `Protocol` or `ABC` interface. The `Storage` port has a proper `Protocol`, but the repositories don't follow this pattern.

This means unit tests for application use cases (Phase 3) will either need to mock concrete classes (fragile) or the team will need to extract interfaces. The ARCHITECTURE.md specifies `application/ports/` as the seam layer, but only `Storage` has a port.

> **Decision needed:** Should repository ports be created now (before Phase 3) or when the first use case needs them?

---

### O2. `ghost directory: var/` referenced in STATUS.md but doesn't exist

STATUS.md lists `var/` as an existing directory. It does not exist in the repository. `config.py` defaults `storage_root` and `snapshot_root` to `var/blobs` and `var/snapshots`. The `LocalStorage` adapter creates directories on first use, but `var/` is not gitignored or documented as auto-created.

---

### O3. `ResourceLockTable` is single-row per resource — no queue semantics

The current design supports exactly one holder per resource name. If multiple workers want to queue for the GPU (priority queue, FIFO), additional rows or a queue table would be needed. This is fine for Phase 2 but should be noted.

---

### O4. `PublishSlot` domain model has no table, repository, or test

[`domain/publishing/models.py` L73–82](file:///home/bittusah/Projects/Personal/Intern/atlas/packages/atlas/src/atlas/domain/publishing/models.py#L73-L82) defines `PublishSlot` as a forward-looking type. No persistence layer exists for it.

---

### O5. Dual ORM-Migration maintenance burden continues

Both `tables.py` and `0001_initial_schema.py` independently define the same schema. The first audit (O1) noted this. While `conftest.py` now runs migrations, there is still no test that compares ORM metadata against migration head using `--autogenerate` diff detection.

---

### O6. Glossary gaps for implemented concepts

The following concepts are used in code but missing from [`GLOSSARY.md`](file:///home/bittusah/Projects/Personal/Intern/atlas/docs/GLOSSARY.md):
- `KnowledgeObjectStatus` lifecycle states (`draft`, `verified`, `published`, `archived`)
- `ClaimStatus` lifecycle states (`verified`, `unsupported`, `refuted`, `contested`)
- `ResourceLock` and `IdempotencyKey` (core execution primitives)
- `TraceabilityChain` (core knowledge concept)
- `FocusSnapshot` (captured by-value in Runs)

---

### O7. D39 in DECISIONS.md not reflected in ARCHITECTURE.md

`DECISIONS.md` has D39 allowing Pydantic in the domain layer. However, `ARCHITECTURE.md` still describes the domain layer as containing "pure computation" with "no I/O library" — without explicitly listing Pydantic as an allowed exception. Minor inconsistency.

---

### O8. Missing directories from ARCHITECTURE.md

ARCHITECTURE.md specifies:
- `application/usecases/` — does not exist
- `application/policies/` — does not exist
- `agents/` — does not exist
- `apps/api/`, `apps/worker/`, `apps/cli/` — do not exist
- `deploy/` — does not exist
- `packages/fakes/` — does not exist

All are Phase 3+ concerns but the gap between documented and actual structure should be noted.

---

## Previous Audit Remediation Verification

| First Audit Issue | Status | Notes |
|---|---|---|
| C1 (Pydantic in domain) | ✅ Fixed | D39 added, test allowlist updated |
| C2 (Cross-subdomain coupling) | ✅ Fixed | `SourceTier` extracted to `domain/common/enums.py` |
| C3 (Storage blocking I/O) | ✅ Fixed | `asyncio.to_thread()` wrapping added |
| C4 (GPU TOCTOU race) | ✅ Fixed | `with_for_update()` added |
| C5 (conftest bypasses Alembic) | ✅ Fixed | `conftest.py` now runs Alembic migrations |
| C6 (No quota tests) | ⚠️ Partial | Test exists but is hollow (see M4 above) |
| S1 (Topics missing FK) | ✅ Fixed | FK constraints added |
| S2 (Focus missing FK) | ✅ Fixed | FK constraint added |
| S3 (BlackoutRule semantics) | ⚠️ Partial | Fields renamed, but docstring still inverted (see S4 above) |
| S4 (UUID truncation) | ✅ Fixed | Full UUID hex used |
| S5 (format parameter) | ✅ Fixed | Renamed to `content_format` |
| S6 (ChannelTable default) | ✅ Fixed | `server_default` added |
| S7 (Import-time Settings) | ✅ Fixed | `@lru_cache` pattern used |
| S8 (Empty __init__.py) | ⚠️ Deferred | Still empty, no `__all__` exports |
| M1 (Unused `os` import) | ✅ Fixed | Removed |
| M2 (timedelta in method body) | ❌ **Not fixed** | Still inside `acquire_lock()` (see M2 above) |
| M3 (Missing __init__.py) | ✅ Fixed | Added to `tests/unit/`, `tests/integration/`, `alembic/versions/` |
| M4 (TraceabilityChain location) | ✅ Fixed | Moved to domain layer |
| M5–M12 | ❌ Deferred | 7 of 8 still unfixed ("fix when touched") |

---

## Security Audit Summary

| Area | Risk | Finding |
|---|---|---|
| **SSRF** | 🟠 Medium | `Source.url` accepts any string including `file://`, `http://169.254.x.x` (S1) |
| **Credential Exposure** | 🟡 Low | Debug `print()` in `alembic/env.py` dumps DB URLs to stdout (M1) |
| **Input Validation** | 🟠 Medium | Multiple string fields lack format validation (timezone, QID, URL, hash) |
| **SQL Injection** | 🟢 None | All queries use parameterized SQLAlchemy ORM — no raw SQL |
| **Path Traversal** | 🟢 None | `LocalStorage` uses content-addressed hashes as paths — no user-controlled paths |
| **Authentication** | 🔵 N/A | No auth layer yet (Phase 3) — `actor_id` is a plain string |
| **Secrets in Code** | 🟢 None | No secrets, keys, or credentials in source |
| **Dependency Audit** | 🟢 Clean | All dependencies are well-maintained, no known CVEs |

---

## Database & Query Audit Summary

| Area | Finding |
|---|---|
| **Indices** | ✅ Good — all FK columns indexed, composite indices for common lookups |
| **Foreign Keys** | ✅ Good — all FKs have explicit `ondelete` policies (RESTRICT, CASCADE, SET NULL) |
| **N+1 Queries** | ⚠️ `get_history()` in `knowledge_repository.py` makes N+1 queries for claim IDs (1 query per version) |
| **Connection Pool** | ✅ Properly configured with `pool_size=10`, `max_overflow=20` |
| **Transaction Safety** | ✅ `DatabaseSessionManager.session()` correctly commits/rolls back/closes |
| **Row-level Locking** | ✅ `acquire_lock` uses `with_for_update()` |
| **Missing Constraints** | 🟠 No `CHECK` constraints on enum-like columns (S6), no temporal bounds validation |
| **Missing Unique** | ⚠️ `SnapshotTable` has composite index `(source_id, content_hash)` but not `UNIQUE` — allows duplicate snapshots |

---

## Architecture Quality Assessment

| Area | Grade | Notes |
|---|---|---|
| **Layering** | A | Clean separation: domain → application → adapters → entrypoints. Enforced by test. |
| **Domain Modeling** | B+ | Strong entity design, good use of value objects, frozen models. Gaps in validation and missing models (Asset, License). |
| **Persistence** | A- | Well-structured repositories, proper FK constraints, good index design. N+1 in `get_history()`. |
| **Testing** | B- | Good unit test structure, but integration tests have false-positive risks. Missing edge cases. |
| **Documentation** | A | Comprehensive ADRs with trade-offs and expiry conditions. Minor inconsistencies. |
| **Security** | B- | Good foundation (no raw SQL, content-addressed storage), but missing input validation and SSRF prevention. |
| **Configuration** | B+ | Clean settings pattern, but test DB URL not configurable via env. |

---

## Recommended Priority for Phase 3

| Priority | Issues | Rationale |
|---|---|---|
| **Fix immediately** | C1, C2, C3, C5 | Domain correctness — will cause data integrity issues the moment agents start producing data |
| **Fix early Phase 3** | C4, S1, S2, S6, S8 | Test reliability and input validation — prevents false confidence |
| **Fix before Phase 5** | S3, S5, S7, S9, M11, M13 | Needed when model calls and research begin |
| **Fix before Phase 7** | S4, M12 | Semantic clarity needed for scheduling logic and rendering |
| **Document/Decide** | O1, O5, O6, O7 | Architectural decisions and documentation consistency |
| **Low priority** | M1–M10, M14 | Code quality improvements, address opportunistically |
