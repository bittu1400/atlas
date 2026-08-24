# Atlas Code Audit — Phase 3.1

**Auditor**: Senior Code Review (30yr)  
**Date**: 2026-08-20  
**Scope**: Full codebase (`packages/`, `apps/`, `tests/`) — code and git only, docs excluded  
**Commits Reviewed**: `38d33fe` → `e594257` (HEAD)

---

## Summary Dashboard

| Severity | Count | Fixed in Phase 2? | New in Phase 3 |
|----------|-------|--------------------|-----------------|
| **P0 — Critical** | 5 | — | 5 |
| **P1 — High** | 8 | — | 8 |
| **P2 — Medium** | 12 | — | 12 |
| **P3 — Low** | 9 | — | 9 |
| **Total** | **34** | 0 | 34 |

---

## P0 — Critical Bugs & Security Issues

### P0-01: Pipeline Claims 17 Stages but Has 18 — Off-by-One

**Category**: Bug  
**Files**: `packages/atlas/src/atlas/application/pipeline/runner.py`, `packages/atlas/src/atlas/application/policies/gate_policy.py`  
**Lines**: runner.py L4, L102, L177; gate_policy.py L34

`PipelineStage` defines **18** stages (including `PUBLISH` as Stage 18), but runner.py docstring and logs say "17 discrete stages" / "completed all 17 stages successfully". `STAGE_SEQUENCE` in the runner contains all 18 entries. The `step_index` field has `ge=1` constraint described as `(1..17)` — should be `(1..18)`.

**Impact**: Misleading logs, documentation drift, potential validation failures if anyone enforces "17 stages" as a business rule.

**Fix**: Update all references from "17" to "18" in runner.py docstrings and notification messages, or re-evaluate whether `PUBLISH` is truly a separate stage.

---

### P0-02: Pipeline Runner Has No Error Handling — Stage Failures Crash Entire Run Silently

**Category**: Bug  
**File**: `packages/atlas/src/atlas/application/pipeline/runner.py`  
**Lines**: L142–L180, L287

`_dispatch_stage_handler` (L311) is called inside `_execute_stage` (L287) with **zero try/except**. If any stage handler raises an exception (e.g., network error, DB error, LLM timeout), it:
1. Propagates up uncaught
2. The Step remains in `RUNNING` status forever (never set to `FAILED`)
3. The Run remains in `RUNNING` status forever (never set to `FAILED`)
4. The idempotency key is never recorded, so re-runs re-attempt

**Impact**: Zombie runs — runs stuck permanently in `RUNNING` state with no way to recover. Data inconsistency.

**Fix**: Wrap `_dispatch_stage_handler` call in try/except, setting `StepStatus.FAILED` and `RunStatus.FAILED` on error, recording the error message.

---

### P0-03: CORS Allows All Origins with Credentials — Security Vulnerability

**Category**: Security  
**File**: `apps/api/main.py`  
**Lines**: L55-61

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,  # ← DANGEROUS with wildcard origins
    allow_methods=["*"],
    allow_headers=["*"],
)
```

`allow_origins=["*"]` + `allow_credentials=True` is a well-known anti-pattern. While FastAPI/Starlette will actually ignore `allow_credentials` when origins are `*` (per CORS spec), the intent is clearly wrong. Any origin can access mutation endpoints (POST `/runs`, POST `/gates/{id}/approve`).

**Impact**: Any website can create pipeline runs, approve/reject gates, and manipulate state on behalf of an operator. No authentication layer exists at all.

**Fix**: Restrict `allow_origins` to specific trusted origins, or add authentication middleware as a prerequisite.

---

### P0-04: No Authentication or Authorization on Any Endpoint

**Category**: Security  
**Files**: All route files in `apps/api/routes/`

Every endpoint is wide open — no auth middleware, no API keys, no tokens. The `actor_id` field in requests is user-supplied and completely trusted:
- `POST /runs` — anyone can create a pipeline run
- `POST /gates/{id}/approve` — anyone can approve a gate
- `POST /gates/{id}/reject` — anyone can reject and abandon a run
- `GET /events/runs/{run_id}` — SSE stream is unauthenticated

**Impact**: Complete system compromise from any network-reachable attacker. Critical for production.

**Fix**: Add API key middleware or JWT authentication. Validate actor_id against authenticated identity.

---

### P0-05: SSE Event Generator Has JSON Injection via `run_id`

**Category**: Security  
**File**: `apps/api/routes/events.py`  
**Lines**: L15, L17

```python
yield f'data: {{"event": "connected", "run_id": "{run_id}", ...}}\n\n'
```

The `run_id` is directly interpolated into a JSON string via f-string without escaping. A crafted `run_id` containing `"` characters (e.g., `run_id = 'x","evil":"payload'`) would break the JSON and inject arbitrary fields into the SSE event stream.

**Impact**: SSE consumers parsing JSON may be fed malicious payloads.

**Fix**: Use `json.dumps()` to properly serialize the event dict instead of f-string interpolation.

---

## P1 — High-Severity Issues

### P1-01: CLI `_get_runner_and_repos()` Leaks Database Sessions — Never Closed

**Category**: Bug / Resource Leak  
**File**: `apps/cli/main.py`  
**Lines**: L64-98

```python
async def _get_runner_and_repos():
    session = await session_manager.get_session()  # ← Raw session, no context manager!
    ...
```

Every CLI command calls `_get_runner_and_repos()` which creates a raw `AsyncSession` via `get_session()` but **never** closes it. There's no `async with` or `finally` block. The session and its database connection are leaked.

**Impact**: Connection pool exhaustion under repeated CLI usage. Uncommitted transactions left dangling.

**Fix**: Use `session_manager.session()` (the context manager) instead, or add a proper cleanup step.

---

### P1-02: CLI Commands Never Commit Transactions

**Category**: Bug  
**File**: `apps/cli/main.py`  

Related to P1-01: since the CLI uses `get_session()` (raw session) and not the `session()` context manager, **no commit ever happens**. All database writes (run creation, step updates, gate approvals) are lost after the CLI exits.

**Impact**: CLI commands appear to succeed but do nothing permanent.

**Fix**: Use the `session()` async context manager which auto-commits on successful exit.

---

### P1-03: `GetQuotaStatusUseCase.execute()` Returns Hardcoded Fake Data

**Category**: Bug  
**File**: `packages/atlas/src/atlas/application/usecases/get_run_status.py`  
**Lines**: L50-59

```python
async def execute(self) -> dict[str, Any]:
    return {
        "status": "healthy",
        "providers": {
            "gemini": {"rpm_remaining": 15, ...},
            ...
        },
    }
```

The quota status use case ignores `self.execution_repo` entirely and returns hardcoded data. The API and CLI expose this as "real-time quota status" to operators.

**Impact**: Operators cannot make informed decisions about quota availability. System may exceed limits silently.

**Fix**: Query `quota_ledger` and `model_calls` tables to compute actual usage.

---

### P1-04: `ListGatesUseCase` Returns Empty List When `pending_only=False`

**Category**: Bug  
**File**: `packages/atlas/src/atlas/application/usecases/get_run_status.py`  
**Lines**: L37-41

```python
async def execute(self, pending_only: bool = True) -> list[Gate]:
    if pending_only:
        return await self.execution_repo.list_pending_gates()
    return []  # ← Always empty for non-pending query!
```

When `pending_only=False`, it returns an empty list instead of querying all gates.

**Impact**: No way to query historical (resolved) gates via the use case. Dead code path.

**Fix**: Add `self.execution_repo.list_all_gates()` or similar for the `pending_only=False` case.

---

### P1-05: Quota Manager In-Memory Rate Limiting Is Not Process-Safe

**Category**: Bug / Concurrency  
**File**: `packages/atlas/src/atlas/platform/quota.py`  
**Lines**: L55-58

Rate limits are tracked with in-memory Python dicts (`_minute_calls`, `_daily_calls`, `_daily_tokens`). In a multi-worker deployment:
- Each worker has independent counters
- Workers can collectively exceed provider limits
- Process restarts reset all counters

**Impact**: Rate limit enforcement is meaningless in production. Provider quotas can be exceeded.

**Fix**: Query the `quota_ledger` table (which already exists) for actual consumption counting, or use Redis for shared counters.

---

### P1-06: `DatabaseSessionManager` Singleton Is Not Thread-Safe

**Category**: Concurrency  
**File**: `packages/atlas/src/atlas/adapters/persistence/database.py`  
**Lines**: L69-77

```python
_session_manager: DatabaseSessionManager | None = None

def get_session_manager() -> DatabaseSessionManager:
    global _session_manager
    if _session_manager is None:
        _session_manager = DatabaseSessionManager()
    return _session_manager
```

No lock protects the singleton creation. Under concurrent startup (e.g., multiple async tasks calling this simultaneously), multiple `DatabaseSessionManager` instances can be created, each with its own engine and connection pool.

**Impact**: Connection pool fragmentation, potential resource leaks.

**Fix**: Use a threading `Lock` to guard the singleton, or use `lru_cache` like `get_settings()`.

---

### P1-07: Route Handlers Catch Exceptions Redundantly (Inconsistent Error Responses)

**Category**: Bug  
**Files**: `apps/api/routes/gates.py` L58-75, `apps/api/routes/runs.py` L83-99

`approve_gate` and `get_run` catch `GateNotFoundError`/`RunNotFoundError` and re-raise as `HTTPException`, but these errors already have registered global exception handlers in `main.py` (L64-96). The route handler's catch blocks convert them to **different HTTP responses** (using `detail=err.message` string) than the global handlers (which return structured JSON with `error`/`message`/`gate_id` fields).

**Impact**: Inconsistent error response format. The route handler's catch takes priority, so the structured global handler is dead code for these endpoints.

**Fix**: Remove the try/except from route handlers and let global exception handlers provide consistent structured responses.

---

### P1-08: Pipeline Runner Re-runs All Stages on Resume — Broad Exception Catch

**Category**: Bug  
**File**: `packages/atlas/src/atlas/application/pipeline/runner.py`  
**Lines**: L154, L197-212

```python
for index, stage in enumerate(STAGE_SEQUENCE, start=1):
    should_suspend, gate = await self._execute_stage(run, stage, index)
```

When a run resumes after gate approval, `run_pipeline` iterates through **all 18 stages from the beginning**. While the idempotency check (L193-213) short-circuits completed stages, this creates:
1. N+1 idempotency key lookups for every previously-completed stage
2. N gate lookups per already-completed stage (L216)
3. Unnecessary DB round-trips

Additionally, the idempotency catch-all `except Exception` at L199 is overly broad — it silently ignores genuine DB errors and creates a new step anyway.

**Impact**: Performance degradation on resume. Silent data corruption if idempotency check fails for non-NotFound reasons.

**Fix**: Track last completed step index on the Run and start from there. Narrow the except clause to `StepNotFoundError`.

---

## P2 — Medium-Severity Issues

### P2-01: `ResponseCache` Is Unbounded — Memory Leak

**Category**: Bug  
**File**: `packages/atlas/src/atlas/platform/cache.py`  
**Lines**: L17

```python
self._cache: dict[str, str] = {}
```

The response cache has no size limit, no TTL, and no eviction policy. LLM responses can be large strings. Over a long-running process, this dictionary grows without bound.

**Impact**: OOM crash in long-running workers.

**Fix**: Use `functools.lru_cache` with `maxsize`, or use `cachetools.TTLCache`.

---

### P2-02: `config.py` Uses `lru_cache` — No Way to Override in Tests

**Category**: Design  
**File**: `packages/atlas/src/atlas/platform/config.py`  
**Lines**: L42-44

`@lru_cache` on `get_settings()` means once instantiated, it cannot be replaced for testing without `get_settings.cache_clear()`. This is fragile.

**Impact**: Test isolation issues if tests modify environment variables after settings are cached.

**Fix**: Accept `get_settings` as an injectable dependency, or document the `cache_clear()` requirement.

---

### P2-03: `FakeSearch` Uses `md5` Instead of `sha256`

**Category**: Security / Consistency  
**File**: `packages/atlas/src/atlas/adapters/fakes/providers.py`  
**Lines**: L129, L135, L157, L166

`hashlib.md5()` is used in fake providers. While these are fakes, MD5 is flagged by security scanners and FIPS compliance tools. Atlas uses SHA-256 everywhere else.

**Impact**: Security scanner noise; inconsistency with project convention.

**Fix**: Replace with `hashlib.sha256()`.

---

### P2-04: `list_runs` API Endpoint Has No Upper Bound on `limit` Parameter

**Category**: Security / Query  
**File**: `apps/api/routes/runs.py`  
**Lines**: L54

```python
limit: int = 50,
```

No `le=` or `max_value` constraint. A client can pass `limit=999999999` causing a massive unbounded query.

**Impact**: DB overload, memory exhaustion, potential DoS.

**Fix**: Add `Query(default=50, ge=1, le=200)`.

---

### P2-05: `create_run` Route Runs Pipeline Synchronously — Blocks HTTP Request

**Category**: Design  
**File**: `apps/api/routes/runs.py`  
**Lines**: L36

```python
updated_run = await runner.run_pipeline(run.id)
```

The POST handler runs the entire pipeline synchronously in the request handler. With real providers, this would block the HTTP request for the full pipeline duration (potentially minutes), exceeding any reasonable timeout.

**Impact**: HTTP timeouts, poor user experience, resource starvation.

**Fix**: Dispatch pipeline to background worker and return 202 Accepted immediately.

---

### P2-06: `approve_gate` Route Also Runs Pipeline Synchronously

**Category**: Design  
**File**: `apps/api/routes/gates.py`  
**Lines**: L61

Same as P2-05 but for the approve gate endpoint.

**Fix**: Background dispatch.

---

### P2-07: Run State Machine Allows Invalid Transitions — No Transition Guards

**Category**: Bug  
**File**: `packages/atlas/src/atlas/adapters/persistence/repositories/execution_repository.py`  
**Lines**: L105-116

`update_run_status` accepts any `RunStatus` and blindly sets it. There's no validation of valid transitions. The domain defines `InvalidStateTransitionError` in errors.py, but it's **never raised anywhere**.

Invalid transitions that would silently succeed:
- `COMPLETED → RUNNING` (restarting a completed run)
- `FAILED → COMPLETED` (marking a failed run as complete)
- `ABANDONED → RUNNING` (resurrecting an abandoned run)

**Impact**: Data integrity — runs can be placed in impossible states.

**Fix**: Add a transition table and validate before updating.

---

### P2-08: `Approval` Table Has `UniqueConstraint("gate_id")` — Prevents Multiple Rejection Attempts

**Category**: Design / Schema  
**File**: `packages/atlas/src/atlas/adapters/persistence/tables.py`  
**Lines**: L604

```python
UniqueConstraint("gate_id", name="uq_approval_gate"),
```

Only one approval record per gate is allowed. If a gate is rejected and a new gate is created for the rework cycle, this is fine. But if the business logic ever needs to record multiple approval attempts (e.g., rejected then approved), the unique constraint blocks it.

**Impact**: Constrains future rework flow design.

**Fix**: Evaluate if the constraint should be `UniqueConstraint("gate_id", "decision")` or removed entirely.

---

### P2-09: `PublishingWindowTable.local_start_time < local_end_time` Constraint Prevents Overnight Windows

**Category**: Bug / Schema  
**File**: `packages/atlas/src/atlas/adapters/persistence/tables.py`  
**Lines**: L438

```python
CheckConstraint("local_start_time < local_end_time", name="pub_windows_time_interval_check"),
```

Same constraint exists on `BlackoutRuleTable` (L459). These prevent overnight windows (e.g., `23:00` to `02:00`). Ironically, the blackout rule itself is "22:00 to 06:00" which spans midnight — the constraint would **reject** the actual blackout rule described in the spec.

**Impact**: Cannot store the specified blackout rule (22:00–06:00) in the database.

**Fix**: Remove or modify the constraint to allow `start > end` (indicating overnight span).

---

### P2-10: `ModelCallTable` FK to Steps Uses `ondelete="SET NULL"` but Has Composite FK

**Category**: Schema  
**File**: `packages/atlas/src/atlas/adapters/persistence/tables.py`  
**Lines**: L671-673

```python
ForeignKeyConstraint(
    ["step_id", "run_id"], ["steps.id", "steps.run_id"], ondelete="SET NULL"
),
```

`step_id` is nullable but `run_id` is `NOT NULL` (it has its own FK to `runs.id` at L644-645). When a step is deleted, `SET NULL` will null out `step_id` but leave `run_id` — this is correct. BUT the composite FK means both columns would be set to NULL, and since `run_id` has `nullable=False`, this will raise a constraint violation.

**Impact**: Deleting a Step row cascades to violate `model_calls.run_id NOT NULL`.

**Fix**: Change to `ondelete="RESTRICT"` or separate the FKs.

---

### P2-11: `approve_gate` Use Case Fetches Gate Twice

**Category**: Query / Performance  
**File**: `packages/atlas/src/atlas/application/usecases/approve_gate.py`  
**Lines**: L39, L57

```python
gate = await self.execution_repo.get_gate(gate_id)          # First fetch
...
recorded_approval = await self.execution_repo.record_approval(approval)
updated_gate = await self.execution_repo.get_gate(gate_id)   # Second fetch (unnecessary)
```

The gate is fetched twice — once for validation (L39) and once to return the updated state (L57). `record_approval` already modifies the gate row in place. The second fetch is unnecessary.

**Impact**: Extra DB round-trip per approval.

**Fix**: Return the gate from `record_approval`, or build the updated gate in memory.

---

### P2-12: Step Index Reuses 1-Based Counter but STAGE_SEQUENCE Has 18 Elements

**Category**: Bug  
**File**: `packages/atlas/src/atlas/application/pipeline/runner.py`  
**Lines**: L154

```python
for index, stage in enumerate(STAGE_SEQUENCE, start=1):
```

The `step_index` in `Step` model has `ge=1` but comments say "(1..17)". Actual max index will be 18 (for PUBLISH). Minor alignment issue with Step.step_index documentation.

---

## P3 — Low-Severity Issues

### P3-01: 6 Pipeline Stages Have No Handler — Fall Through to `return "completed"`

**Category**: Dead Code / Incomplete  
**File**: `packages/atlas/src/atlas/application/pipeline/runner.py`  
**Lines**: L687

Stages without explicit handlers in `_dispatch_stage_handler`: `TOPIC_SELECTION`, `KNOWLEDGE_OBJECT`, `STORY_ANGLE`, `SCRIPT_APPROVAL`, `ASSET_SELECTION`, `FINAL_APPROVAL`.

These fall through the if/elif chain and hit the final `return "completed"` at L687. However, all of these are `GateType.MANUAL` in the gate policy, so the gate suspension is created before the handler is called. The handler is effectively dead code for these stages — but if the gate policy is changed to AUTOMATIC, they'd silently do nothing.

**Impact**: Silent failures if gate policy is reconfigured for these stages.

**Fix**: Add explicit handlers or a clear `raise NotImplementedError` for unhandled stages.

---

### P3-02: `InvalidStateTransitionError` Is Defined But Never Used

**Category**: Dead Code  
**File**: `packages/atlas/src/atlas/platform/errors.py`  
**Lines**: L112-118

Defined in errors.py but no code raises it.

**Fix**: Wire it into `update_run_status` (see P2-07) or remove.

---

### P3-03: `InvalidGateDecisionError` Is Defined But Never Used

**Category**: Dead Code  
**File**: `packages/atlas/src/atlas/platform/errors.py`  
**Lines**: L108-109

**Fix**: Wire it into gate validation or remove.

---

### P3-04: `StepExecutionError` Is Defined But Never Used

**Category**: Dead Code  
**File**: `packages/atlas/src/atlas/platform/errors.py`  
**Lines**: L121-127

**Fix**: Use it in the pipeline runner error handling (P0-02 fix) or remove.

---

### P3-05: `AiImageUnapprovedError` Is Defined But Never Used

**Category**: Dead Code  
**File**: `packages/atlas/src/atlas/platform/errors.py`  
**Lines**: L180-187

**Fix**: Wire it into the asset selection gate enforcement or remove.

---

### P3-06: `BlackoutWindowViolationError` Is Defined But Never Used

**Category**: Dead Code  
**File**: `packages/atlas/src/atlas/platform/errors.py`  
**Lines**: L194-201

**Fix**: Wire it into publishing window validation or remove.

---

### P3-07: `SchedulingError` Is Defined But Never Used

**Category**: Dead Code  
**File**: `packages/atlas/src/atlas/platform/errors.py`  
**Lines**: L190-191

**Fix**: Wire it into scheduling logic or remove.

---

### P3-08: Specialized ID Generators in `ids.py` Are Mostly Unused

**Category**: Dead Code  
**File**: `packages/atlas/src/atlas/platform/ids.py`  
**Lines**: L15-72

Functions like `generate_ko_id()`, `generate_claim_id()`, `generate_evidence_id()`, `generate_source_id()`, `generate_snapshot_id()`, `generate_step_id()`, `generate_gate_id()`, `generate_approval_id()`, `generate_topic_id()`, `generate_focus_id()`, `generate_domain_id()` exist but the codebase predominantly uses `generate_id("prefix")` directly instead.

**Impact**: Dead code, maintenance burden.

**Fix**: Either use the dedicated functions consistently or remove them.

---

### P3-09: `logger.warn()` Used Instead of `logger.warning()` in Quota Manager

**Category**: Code Quality  
**File**: `packages/atlas/src/atlas/platform/quota.py`  
**Lines**: L77

```python
logger.warn("quota.rate_limit_hit", ...)
```

`warn()` is a deprecated alias for `warning()` in standard logging. While structlog may handle it, it's inconsistent.

**Fix**: Use `logger.warning()`.

---

## Additional Findings Discovered During Audit

These are additional issues found during the audit that don't fall neatly into the categories above but should be addressed.

### AF-01: Worker `main.py` Poll Loop Is a No-Op

**File**: `apps/worker/main.py`  
**Lines**: L17-21

When no `run_id` argument is passed, the worker just prints a message and exits. There's no actual polling loop, no queue subscription, no sleep/retry logic.

**Severity**: P2

---

### AF-02: `RoutingPolicy` Is Defined But Never Referenced in Pipeline Runner

**File**: `packages/atlas/src/atlas/application/policies/quota_policy.py`

`RoutingPolicy` and `TaskKind` define the full task-to-model routing table but the pipeline runner hardcodes `"fake"` provider directly rather than routing through the policy. The entire file is effectively unused.

**Severity**: P3

---

### AF-03: No Global Unhandled Exception Handler for Non-AtlasError Exceptions in API

**File**: `apps/api/main.py`

Global handlers exist for `AtlasError` subclasses but not for generic `Exception`. An unexpected exception (e.g., DB connection error, third-party library crash) returns FastAPI's default 500 with a stack trace that may leak internal implementation details.

**Severity**: P2

---

### AF-04: `FakePublisher` and `FakeSpeech` Are Defined But Never Injected

**File**: `packages/atlas/src/atlas/adapters/fakes/providers.py`

`FakePublisher` (L262) and `FakeSpeech` (L284) are defined but never instantiated in `dependencies.py`, `tasks.py`, or `cli/main.py`. They're orphaned fakes.

**Severity**: P3

---

### AF-05: `SourceRepository.link_evidence_to_claim` Has an Alias `link_claim_evidence`

**File**: `packages/atlas/src/atlas/adapters/persistence/repositories/source_repository.py`  
**Lines**: L256

```python
link_claim_evidence = link_evidence_to_claim
```

Two names for the same method. The port interface uses `link_claim_evidence`, but the implementation is `link_evidence_to_claim` with an alias. Not a bug, but confusing and should be cleaned up.

**Severity**: P3

---

### AF-06: `get_run` Route Handler Catches `RunNotFoundError` Redundantly

**File**: `apps/api/routes/runs.py`  
**Lines**: L83-99

Same issue as P1-07 — the route handler catches `RunNotFoundError` and raises `HTTPException`, but the global handler in `main.py` already handles this with a structured JSON response.

**Severity**: P1 (duplicate of P1-07 pattern)

---

### AF-07: `reject_gate` Route Handler Does Not Resume Pipeline After Rework

**File**: `apps/api/routes/gates.py`  
**Lines**: L78-113

Unlike `approve_gate` which calls `runner.run_pipeline()` after approval, `reject_gate` does **not** inject or call the pipeline runner. This means the `queue_broker.enqueue()` call in the use case (L80 of `reject_gate.py`) doesn't actually trigger any execution since `FakeQueueBroker` is just an in-memory list.

**Severity**: P2

---

## Phase 3.1 Remediation Plan

Items are prioritized for the **next session**. P0 items must be fixed first, followed by P1s.

### Must Fix (P0 — Next Session)
1. **P0-01**: Fix stage count references (17→18)
2. **P0-02**: Add error handling in pipeline runner stage execution
3. **P0-03**: Fix CORS configuration
4. **P0-04**: Add authentication middleware (at minimum API key)
5. **P0-05**: Fix SSE JSON injection

### Should Fix (P1 — Next Session)
6. **P1-01/P1-02**: Fix CLI session management (use context manager)
7. **P1-03**: Wire `GetQuotaStatusUseCase` to actual DB data
8. **P1-04**: Implement `pending_only=False` branch
9. **P1-05**: Document multi-worker limitation, add TODO for Redis
10. **P1-06**: Fix singleton thread safety
11. **P1-07/AF-06**: Remove redundant try/except in route handlers
12. **P1-08**: Narrow `except Exception` to `StepNotFoundError`

### Nice to Fix (P2 — Session After Next)
13. **P2-01**: Add cache size limit
14. **P2-04**: Add upper bound to limit parameter
15. **P2-05/P2-06**: Add background dispatch for pipeline execution
16. **P2-07**: Add state transition validation
17. **P2-09**: Fix overnight window constraint
18. **P2-10**: Fix composite FK SET NULL conflict
19. **P2-11**: Remove redundant gate fetch
20. **AF-01**: Implement worker poll loop
21. **AF-03**: Add global unhandled exception handler
22. **AF-07**: Wire reject pipeline resumption

### Cleanup (P3 — Session After Next)
23. Dead code removal: P3-02 through P3-08
24. **P3-09**: Fix `warn()` → `warning()`
25. **AF-02**: Wire or remove `RoutingPolicy`
26. **AF-04**: Wire or remove `FakePublisher`/`FakeSpeech`
27. **AF-05**: Clean up method alias

---

## Stats

- **Files audited**: 65 Python source files + configuration
- **Total issues found**: 34 primary + 7 additional findings = **41 total**
- **Lines of code reviewed**: ~7,500 LoC (excluding tests, excluding docs)
- **Architecture**: Generally sound — clean separation, ports/adapters, typed errors
- **Test coverage**: Present but not evaluated in this phase (code-only audit)

If all P0 and P1 items are fixed in the next session, this codebase will be in solid shape for Phase 4 work. The P2/P3 items are real but non-blocking.
