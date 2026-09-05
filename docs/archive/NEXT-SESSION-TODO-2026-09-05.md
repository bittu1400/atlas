> **SUPERSEDED — nothing in this file is a current claim.**
>
> This is the working document the 2026-09-05 five-angle verification produced. Its content was
> folded into `docs/AUDIT-2026-08-29.md` **§19**, which is the authoritative register, and its
> ordered list into **§19.10**. It is kept here as evidence of what that session actually wrote,
> under the convention `docs/archive/` already carries. **Decision D151.**
>
> Two things here are out of date, and the body is deliberately **not** edited — an archived document
> is the record of what a session wrote, not a live claim:
>
> 1. The first draft of **V-49** claimed six missing indexes on hot paths. That was wrong; it is
>    corrected inside this file and again in §19.8. Read **§19.6**, not this.
> 2. This file stops at **V-83** (64 findings). A closing sweep after it was written added
>    **V-84 – V-89** — the uncalled `validate_claim_publication_readiness` and five ADR divergences —
>    bringing the total to **70, V-20 – V-89**. §19 is complete; this file is not.

---

# Next session — the complete, evidence-backed TODO

**Written:** 2026-09-05, in a session that **changed no code, no configuration and no document**. The
only file it created is this one.
**Scope of that session:** the five-angle verification `docs/AUDIT-2026-08-29.md` §18 asked for, run
read-only. Findings were recorded, not fixed — §18.0 rule 4.
**Status of every finding below:** confirmed by a command whose raw output is quoted, or by a file
and line you can open. Nothing here is inferred from a document.

**Method, stated honestly, because it changes how much weight to put on each finding.** This file is
the product of **two** passes.

- **First pass — not run as §18.7 specifies.** It was one interleaved sweep, sorted into five
  sections afterwards, and it was steered by §18.2–§18.6's own "things to distrust" lists rather than
  by reading the tree cold. That is docs-first, which is the failure mode §18.0 warns about: it finds
  what somebody already suspected. Findings **V-20 – V-57** come from it.
- **Second pass — five separate passes over the code, in order, reading modules the first pass never
  opened** (the agents, the domain models, the prompt loader, the fetcher, the storage adapter, the
  approval components, the backup tooling, the guards themselves). Findings **V-58 – V-83** come from
  it, and it produced one **correction** to the first pass (V-49). The second pass found the more
  serious defects — V-58, V-71, V-75 and V-80/V-81 are all worse than anything in the first — which
  is the argument for doing it that way round from the start.

Both passes are read-only. Neither ran a provider call.

> **This file is not the register.** `docs/AUDIT-2026-08-29.md` is. Your first act should be to
> transcribe §2–§6 below into a new **§19** of that file and add the tasks to **§15.9**'s ordered
> list, then delete this file or archive it under `docs/archive/`. Two registers is how the
> disagreement between documents starts.

---

## 0. Baseline, re-measured before anything (R7)

Every command was run in the session that wrote this file, on branch `docs/audit-2026-08-29`, clean
tree. **Re-run them before quoting them.**

```
$ uv run ruff check .
All checks passed!

$ uv run mypy .
Success: no issues found in 179 source files

$ uv run pytest
191 passed in 20.55s

$ uv run pre-commit run --all-files
Ruff Lint Check..........................................................Passed
Ruff Format Check........................................................Passed
Anti-Fabrication Structural Guard........................................Passed

$ pnpm test
10 passed (5.7s) — apps/web/e2e/dashboard.spec.ts, Playwright Chromium

$ pnpm -r build
packages/tokens · apps/renderer · apps/web — 3 of 3 built

$ uv run python -c "from apps.api.main import app; ..."
15 paths, 20 operations — matches ARCHITECTURE §2.1 row for row, including the two unauthenticated ones

$ psql atlas_test -Atc "select count(*) from information_schema.tables where table_schema='public'"
31   # 30 tables + alembic_version, at head b1c4d7e90a25
```

**Six of the seven §18.1 numbers hold. One does not:**

| §18.1 claim | Measured | Verdict |
|---|---|---|
| ruff clean · mypy 179 files · 191 tests · 10 browser tests · 3 builds | identical | holds |
| 30 tables · 7 migrations · HTTP 15/20 | identical | holds |
| Container port wiring (11 ports) | identical | holds |
| **36 test modules** | **33 `test_*.py`; 38 `.py` under `tests/`** | **wrong — finding V-57** |

Two live-database facts you should know before you start, both read from the **application**
database `atlas` (untouched by this session):

```
runs: 0        focus: 0 rows        active_focus: 0 rows
domains: 4     topics: 3            channels: 3
dom_history.research_profile.source_tier_floor = "primary"   # T-66's restore held
```

No Run has ever existed in the application database. There is no Focus and no Active Focus pointer.
See V-37 and V-56.

---

## 1. How to work this list

1. **Record before fixing** (§18.0 rule 4). Transcribe into `AUDIT-2026-08-29.md` §19 first.
2. **A passing test is a claim.** Four findings below (V-49, V-50, V-53, V-54) are about tests that
   pass over the thing they name. Before trusting any test, ask what it would do if the feature were
   deleted.
3. **Do not spend Gemini quota.** T-34 is still sequenced behind T-29, T-30, T-58 — and V-40 says
   the first real call would 404 anyway.
4. **One fix at a time, with the failing test first.** V-17 was a fix that became the next defect.
5. Severities: **P0** = data loss, security, or a claim in `STATUS.md` that is false. **P1** =
   the system does not do what a document says it does. **P2** = wrong but contained. **P3** =
   hygiene.

---

## 2. Angle 1 — Bugs

### V-20 · P0 · A failed stage destroys the entire record of the Run

`apps/api/dependencies.py:62` (`get_db_session`) → `packages/atlas/src/atlas/adapters/persistence/database.py:47-58`
(`DatabaseSessionManager.session` rolls back on any exception) → `packages/atlas/src/atlas/application/pipeline/runner.py:369-386`
(`_execute_stage` writes `steps.FAILED` and `runs.FAILED`, then re-raises `StepExecutionError`).

FastAPI resolves `get_db_session` **once per request** and hands the same session to
`CreateRunUseCase` and to `PipelineRunner`. Nothing commits until the request ends. When a stage
raises, the session rolls back and every row the request wrote disappears: the `runs` row, every
`steps` row, every `gates` row, every `model_calls` row and every `quota_ledger` row.

**Measured.** A probe that replaced only the runner with one that raises at stage 1 (no network, no
provider call), against `atlas_test`:

```
POST /runs with failing stage -> 500 {"error":"StepExecutionError","message":"Step 'idea_discovery' failed: probe: provider unavailable","step_name":"idea_discovery"}
rows in runs: 0
rows in steps: 0
rows in gates: 0
rows in domains: 6      # earlier successful requests committed normally
rows in topics: 1
rows in channels: 4
```

The log line `run.created run_id=run_d882a94f9b6540acb168b200ffc0aa30` was emitted. That run does not
exist.

**All three entry points have it.** `apps/cli/main.py:77-89` (`_managed_cli_context`) wraps every
command in the same `session_manager.session()`; `apps/worker/tasks.py:16` does the same.

**What it breaks:** **R11** (never destroy evidence of a failure — failed runs *are* the audit
trail), **Invariant 7** (an artifact records how it was made — the `model_calls` rows for calls that
really happened are rolled back), **Invariant 8** (an unmetered call is a bug — a real Gemini request
that then fails leaves no `quota_ledger` row, so Atlas forgets it spent scarce budget), and
`STATUS.md` §4's "hitting it destroys thirteen completed stages", which understates it: it destroys
the Run itself.

**Why no test saw it:** every integration test uses the `db_session` fixture, which rolls back at
teardown regardless (`tests/conftest.py:57-59`), and the e2e tests call `runner.run_pipeline`
directly rather than through the HTTP layer. See V-50.

**T-69 — commit the Run record before executing, and never roll back the failure trail.**
*Done when:* a test creates a Run through `POST /runs` (and one through `atlas run create`) with a
stage that raises, and then, **in a new session**, asserts the `runs` row exists with
`status='failed'` and a non-null `error`, the failed `steps` row exists, and any `model_calls` /
`quota_ledger` rows written before the failure survive. The natural fix is a transaction boundary per
stage rather than per request, which is the same seam T-67/T-68 need — do them together.

---

### V-21 · P1 · A rejected Gate deadlocks the Run permanently

`packages/atlas/src/atlas/application/usecases/reject_gate.py:78-88` sets the Run to `REWORKING` and
enqueues. `packages/atlas/src/atlas/application/pipeline/runner.py:270-273`:

```python
elif existing_gate.status == GateStatus.REJECTED:
    # Gate was rejected; keep run suspended/reworking
    return True, existing_gate
```

`run_pipeline` then sets the Run to `SUSPENDED` and returns. Nothing anywhere clears, replaces or
re-opens a rejected gate; no stage re-runs. `REGENERATE` and `BRANCH` (SPEC §7) are recorded in the
`approvals` row and then have no effect.

Worse for the operator: the rejected gate is no longer `pending`, so it vanishes from
`GET /gates/pending` and from the Approval Queue. The Run sits at `suspended` with **no available
action** — see V-39.

`POST /gates/{id}/reject` does not even call the runner (`apps/api/routes/gates.py:74-100` takes no
`PipelineRunner`), and `InlineQueueBroker.enqueue` only logs, so today the run stops at `REWORKING`
and moves to `SUSPENDED` the next time anything calls `run_pipeline`.

**Why no test saw it:** `tests/integration/test_pipeline_execution_e2e.py:328` is named
`test_gate_structured_rejection_with_rework` and asserts the Run reaches `REWORKING` and that double
resolution is blocked. **It never calls `run_pipeline` again.** No rework is tested.

**T-70 — make a rejection do what SPEC §7 says, or record that it cannot.**
*Done when:* a test rejects a gate with `action=regenerate`, resumes the Run, and asserts the stage
re-executed (new Step or new artifact ref) and the Run left `reworking`; and `action=branch` has a
defined, tested outcome. If the decision is that rework is out of scope for now, the reject path must
refuse `regenerate`/`branch` loudly instead of accepting them and stalling, and `SPEC.md` §17.3 must
say so.

---

### V-22 · P1 · An unknown `focus_id` is a 400, where an unknown `topic_id` is a 404

`FocusNotFoundError` (`packages/atlas/src/atlas/platform/errors.py:112`) subclasses
`FocusError` → `AtlasError`. `apps/api/main.py` registers handlers for `TopicNotFoundError`,
`ChannelNotFoundError`, `DomainNotFoundError` — **not** `FocusNotFoundError` — so it falls through to
the generic `AtlasError` handler at `apps/api/main.py:215-220`, which returns **400**.

`CreateRunUseCase` reaches it at `usecases/create_run.py:65` because `FocusRepository.get_focus`
raises where `get_topic`/`get_domain`/`get_channel`/`get_entity` return `None`
(`focus_repository.py:135-140`).

**Measured, same probe:**

```
POST /runs unknown focus_id -> 400 {"error":"FocusNotFoundError","message":"Focus 'foc_does_not_exist' not found"}
POST /runs unknown topic    -> 404 {"error":"TopicNotFoundError","message":"Topic 'nope' not found","topic_id":"nope"}
```

This is V-16's shape and V-16's fix did not cover it, exactly as §18.2 predicted. It is also a second
inconsistency: the 400 body carries no `focus_id` field, unlike its three siblings.

**T-71 — one convention for "referenced row does not exist".**
*Done when:* every `*NotFoundError` in `platform/errors.py` either has a 404 handler or a documented
reason not to; the repository `get_*` methods agree on raise-vs-`None`; and an HTTP test asserts the
404 body for `focus_id`, alongside the two that already exist for topic and channel.

---

### V-23 · P2 · Stage 5 reports `all_claims_verified` whatever happened

`packages/atlas/src/atlas/application/pipeline/runner.py:485-516`. `FACT_VERIFICATION` returns the
literal string `"all_claims_verified"` on every path — including when
`knowledge_repo.get_current_for_topic` returns `None`, when the Knowledge Object has zero claims, and
when verification marked claims `unsupported` or `refuted` two lines earlier.

That string is written to `steps.output_artifact_ref` and is rendered to the operator by the Pipeline
tab (`apps/web/src/components/RunPipeline.tsx`). It is a sentence about the state of the knowledge
graph that was never measured — the same class of thing R13 forbids the front end to do, produced by
the back end instead.

The sibling stages are honest counts (`ideas_count_N`, `extracted_claims_N`, `assets_found_N`).

**T-72 — stage outputs state what happened, not what was hoped.**
*Done when:* `FACT_VERIFICATION` returns a count (`verified_N_of_M`, or an artifact ref), a test
asserts the ref for a Run whose Knowledge Object has an unsupported claim, and the six
`gate_passed_{stage}` literals are reviewed for the same problem.

---

### V-24 · P2 · Two listing docstrings describe an ordering the code does not use

- `packages/atlas/src/atlas/adapters/persistence/repositories/focus_repository.py:70-73` —
  `"""List every Domain, by name, for an operator choosing one."""` orders by `DomainTable.id`.
- `packages/atlas/src/atlas/adapters/persistence/repositories/publishing_repository.py:51-56` —
  same shape.

`ARCHITECTURE.md` §2.1 says "by ID" for both, so the table is right and the docstrings are wrong.
Trivial, but it is literally the Angle-1 question: where does the code do something other than what
it says.

**T-73 — fix the two docstrings, or the two `order_by` clauses.** *Done when:* docstring, code and
§2.1 agree, decided in one direction.

---

### V-25 · P2 · Invariant 9's trigger is a substring match over a discarded search

Two problems in one path.

1. **Trigger.** `runner.py:294-302` decides whether the asset-selection gate must be MANUAL by
   testing `"_ai" in s.output_artifact_ref`, where that ref is the string
   `f"assets_found_{len(candidates)}{'_ai' if has_ai else ''}"` built at `runner.py:541-549`. A
   presence flag for a human-approval invariant is being smuggled through a substring of a display
   string.
2. **Different lists.** Stage 11 searches `limit=10`; stage 13 re-searches
   `limit=max(5, len(script.beats))` (`runner.py:553-556`). Licenses and the AI flag are validated at
   stage 11 over one candidate list, and the human approves at stage 12; stage 13 then validates and
   uses **a different list**. An AI asset that appears only in the stage-13 result fails the Run at
   `LicensePolicy.validate_ai_image_approval`; one that appears only at stage 11 forces a gate over an
   asset that is never used.

Mitigating: `ASSET_SELECTION` is `MANUAL` unconditionally in `DEFAULT_STAGE_GATES`, so the gate always
suspends anyway, and the real enforcement is `validate_ai_image_approval` at stage 13 against an
`Approval` row. So Invariant 9 is not currently bypassable — but it is held up by a coincidence, and
`STATUS.md`'s invariant table credits the mechanism rather than the coincidence.

This is the deeper half of **T-54** (persist asset candidates at stage 11); note it there.

**T-74 — the AI flag must be a field, not a substring, and stage 13 must use the approved list.**
*Done when:* stage 11 persists its candidate list, stage 13 reads it instead of re-searching, the AI
flag is read from a column, and a test proves an AI asset present at stage 13 but absent at stage 11
can no longer exist.

---

### V-26 · P2 · The renderer blocks the event loop and swallows ffmpeg's reason

`packages/atlas/src/atlas/adapters/renderer/stub.py:88-135`. `async def render` calls
`subprocess.run(...)` three times synchronously. In the API process — which executes the pipeline
inside the request (V-19) — that stalls every other connection for the length of the render.

`check=True, capture_output=True` means a non-zero exit raises `CalledProcessError`, whose `str()` is
`Command '[...]' returned non-zero exit status 1.` — ffmpeg's stderr is captured and then discarded.
A render failure arrives with no reason attached.

Verified clean, for the record: the arguments are a list, `shell=False`, and every interpolated value
(`width`, `height`, `duration`) is a validated number. **No command injection.**

**T-75 — `asyncio.to_thread` (or `create_subprocess_exec`) and log ffmpeg's stderr on failure.**
*Done when:* a failing ffmpeg invocation produces a log line containing its stderr, and a test
asserts it.

---

### V-27 · P3 · The idempotency cache-hit path writes a hash where an artifact ref belongs

`runner.py:229-246`. When an idempotency key exists but the `steps` row does not, the recovery path
creates the Step with `output_artifact_ref=existing_key.output_hash` — a sha256 digest. Every other
path writes a real reference (a Script ID, a Snapshot ID, a comma-joined artifact list), and
`_stage_output` (`runner.py:388-399`) hands whatever it finds straight to
`production_repo.get_script(...)`.

Unreachable today, because `record_idempotency_key` is always preceded by a `create_step`. It becomes
reachable the moment steps are ever pruned, or a stage is re-attributed. It also documents that the
"idempotency key" does not do what ADR-0001 says: the key is
`f"{run_id}:{stage}:{sha256(run_id:stage:focus_id)}"` — **the input hash contains no input**, so it
cannot detect that a stage's inputs changed, and the cache hit returns nothing to the caller.

**T-76 — decide whether the idempotency key is a resume marker or an input hash, and name it that.**
*Done when:* either the hash covers real inputs and a test proves a changed input re-executes the
stage, or ADR-0001's bullet is amended and the field is renamed.

---

### V-28 · P3 · The same row is mapped in four places

`execution_repository.py` builds a `Gate` inline in `get_gate` (298), `list_gates_for_run` (313),
`list_pending_gates` (335) and `list_all_gates` (357) — four copies. `Run` + `FocusSnapshot` is built
inline in `get_run` (102) and `list_runs` (160) — two copies, including the `datetime.fromisoformat`
branch. `source_repository.py` builds `Snapshot` inline in `get_snapshot` and `find_snapshot_by_hash`.

§18.2 asked whether the new `_to_*` mappers are the only mapping path. **For Domain, Topic, Channel
and Focus: yes, confirmed.** For Run, Gate and Snapshot the drift they were introduced to prevent is
still there, in the older repository.

Separately, `ApproveGateUseCase.execute` (`approve_gate.py:47-56`) and `RejectGateUseCase.execute`
(`reject_gate.py:61-70`) each construct a **second** `Gate` carrying the resolved status, duplicating
the transition `ExecutionRepository.record_approval` actually performs on the row. Two places decide
what "approved" means; the returned object is not read back from the database. Both use cases also
open with `if not gate:` after a `get_gate` that raises rather than returning `None` — dead code.

**T-77 — extract `_to_run`, `_to_gate`, `_to_step`, `_to_snapshot`; return the persisted gate.**
*Done when:* each row type has one mapping function, the approve/reject use cases return what
`record_approval` wrote, and CLAUDE.md's "second occurrence means extract" holds in
`execution_repository.py`.

---

### Second pass — the agents, the prompts and the domain models

The first pass never opened `application/agents/`, `domain/`, or `prompts/loader.py`. Everything from
here to the end of this section came out of reading them.

### V-58 · P0 · The only thing allowed to verify a claim promotes it on a substring, and defaults to "verified"

`application/agents/models.py:66-70`:

```python
class VerificationResultItem(BaseModel):
    status: str = Field(default="verified", description="verified, unsupported, refuted, contested")
```

`application/agents/verification.py:107-116`:

```python
raw_status = result.status.lower()
if "verif" in raw_status:      status = ClaimStatus.VERIFIED
elif "refut" in raw_status:    status = ClaimStatus.REFUTED
elif "contest" in raw_status:  status = ClaimStatus.CONTESTED
else:                          status = ClaimStatus.UNSUPPORTED
```

Two failures, both in the direction of false verification.

1. **A missing `status` field defaults to `"verified"`.** A model that returns a rationale and no
   verdict promotes the claim. The safe default for a missing verdict is `unsupported`.
2. **Substring matching on a free string.** `"unverified"` contains `"verif"` → **VERIFIED**. So do
   `"not verified"`, `"cannot be verified"`, `"unverifiable"`. `unverified` is a real `ClaimStatus`
   value and a term the model sees throughout Atlas's vocabulary, so this is not an exotic output.

`VerificationAgent` is the **only** component allowed to move a Claim to `VERIFIED`
(`STATUS.md` §2's invariant table), and `PipelineRunner._assert_script_claims_are_traceable`
gates rendering on exactly that status. So a model saying *"I cannot verify this"* renders it.

Invariant 2: "Language models extract, structure, rank, phrase, and judge. They do not supply facts.
Unsupported claims are marked unsupported and dropped — never backfilled." Both halves of this
defect backfill.

The prompt asks for the four enum values (`prompts/fact_verification_v1.txt:26`), so the happy path
works. Nothing enforces the happy path, and no test asserts what string the model must return.

**T-103 — type the verdict as the enum, required, and delete the substring ladder.**
*Done when:* `VerificationResultItem.status` is `ClaimStatus` with **no default**, Pydantic rejects
anything else, `verification.py` maps it directly, and parametrized tests assert that `"unverified"`,
`"not verified"`, an unknown string, and a missing field each end as `UNSUPPORTED` — never
`VERIFIED`. Add the failing test first; it is a two-line reproduction.

---

### V-59 · P1 · The quality judge invents a passing score for every dimension the model omits

`application/agents/judge.py:99-110`:

```python
scores_by_dim = {s.dimension: s for s in judge_payload.scores}
for dim in RubricDimension:
    if dim in scores_by_dim: ...
    else:
        score_val = 80.0
        reason_text = "Default baseline score."
```

`QualityJudgePayload.scores` requires `min_length=8` but **does not require eight distinct
dimensions** (`agents/models.py:170-174`). Eight copies of one dimension validates, collapses to one
key, and Atlas then supplies **seven scores of 80.0 that no model produced**.

`QualityReport.evaluate` (`domain/quality/models.py:84-90`) passes when weighted ≥ 78.0, no dimension
< 60.0, and all deterministic checks pass. Seven invented 80s clear both score conditions. So a judge
response carrying almost no information yields a **passing quality report**, persisted with
provenance naming the judge, and shown to the operator as a rubric evaluation.

This is the back end doing what R13 forbids the front end to do: rendering an invented number as a
measurement.

**T-104 — a missing dimension is a failed evaluation, not an 80.**
*Done when:* `QualityJudgePayload` requires the eight distinct dimensions (a validator, not a length),
a missing one raises rather than defaulting, and a test asserts that a payload with one dimension
repeated eight times does **not** produce `passed=True`.

---

### V-60 · P1 · Two of the six "binary, non-negotiable" deterministic checks are hardcoded `True`

`application/agents/judge.py:140-147`:

```python
deterministic_checks = {
    "duration_bounds": duration_valid,
    "sourcing_integrity": sourcing_valid,
    "captions_valid": captions_valid,
    "word_budget": words_valid,
    "loudness_bounds": True,
    "safe_margins": True,
}
```

SPEC §8.3 calls these "binary, non-negotiable". Nothing measures loudness anywhere in Atlas —
`AudioCompositor`, which carries the `loudnorm` filter, is an orphan — and nothing computes a
title-safe margin. The quality report tells the operator both checks passed.

**T-105 — measure them or remove them from the report.**
*Done when:* either the two checks are computed from the artifact, or they are absent from
`deterministic_checks` and `SPEC.md` §17.5 records that two of six are unimplemented. A check that
cannot fail must not appear beside checks that can.

---

### V-61 · P1 · Any source containing a backslash-digit sequence crashes the extraction stage

`prompts/loader.py:76-78` substitutes with `re.sub` and an **unescaped replacement string**:

```python
pattern = re.compile(rf"{{\s*{re.escape(key)}\s*}}")
rendered = pattern.sub(str(val), rendered)
```

`re.sub` interprets backslash escapes in the *replacement*. Probed:

```
$ render_prompt('claim_extraction_v1', ..., source_text=r'see backref \1 here')
RAISED: PatternError invalid group reference 1 at position 13
```

`source_text` is arbitrary bytes fetched from the internet. `\1`, `\g<0>` and friends appear in code
samples, regex documentation, LaTeX and Windows paths. Any such source kills stage 4 — and by
**V-20** the entire Run then disappears. `\\` silently collapses to `\`, corrupting the text the model
sees and therefore the verbatim check.

**T-106 — substitute with a function, not a replacement string.**
*Done when:* `pattern.sub(lambda _m: str(val), rendered)` (or `re.escape`-equivalent) is in place and
a test renders a prompt whose value contains `\1`, `\g<1>` and `\\` unchanged.

---

### V-62 · P1 · Stage 14 composes a SoundTrack and throws it away

`runner.py:577-580`:

```python
soundtrack = await self.sound_design_agent.compose(storyboard.id, timing_plan)
return soundtrack.id
```

There is **no `save_soundtrack`**, no `soundtracks` table, and no `SoundTrack` in `ProductionRepository`
(its methods are script, timing plan, storyboard, render artifact — nothing else). So
`steps.output_artifact_ref` for `sound_design` names a `snd_…` ID that resolves to nothing, and stage
15 never receives it: `StubRenderer.render` takes no soundtrack and generates a silent `anullsrc`
track.

ADR-0016 ("production artifacts are persisted") lists four tables and omits this one. `STATUS.md` §2
lists "sound design" among the completed Phase 5 agents. The stage runs, the object is garbage
collected, and nothing downstream can tell.

This is the shape §18.5 asked to look for — "work performed and thrown away" — and stage 1 was not
the only instance.

**T-107 — persist the SoundTrack and read it at render, or delete the stage.**
*Done when:* either a `soundtracks` table exists, ADR-0016 is amended to five artifacts, and the
renderer reads it; or stage 14 is removed and `STATUS.md` §3 says sound design does not exist.

---

### V-63 · P2 · The script schema permits durations the Timing Plan work is not scoped against

`agents/models.py:135-137`: `duration_seconds: float = Field(default=3.5, ge=0.5, le=10.0)`, and
`ScriptPayload.beats` has `min_length=1` with **no maximum**.

So the *schema-permitted* total is **0.5 s to unbounded**, against a judge that accepts 58–62 s. V-14
and T-61 are scoped against the *prompt-compliant* band (36–81 s). The band that actually gates is
much wider, and a one-beat script validates.

Add to **T-61**'s brief. Also note the prompt carries two budgets that can contradict each other:
12–18 beats × 3.0–4.5 s and 110–150 words at 2.0–2.5 wps
(`prompts/script_generation_v1.txt:5-9`).

---

### V-64 · P2 · The word-budget check is looser than the budget

`judge.py:154`: `words_valid = 100 <= script.total_words <= 160`. SPEC §4.2 and the prompt both say
**110–150**. The gate accepts ten words of slack on each side, silently. Fold into **T-61** or **T-105**.

---

### V-65 · P2 · A hard gate has an override hook with no caller

`judge.py:52` — `deterministic_overrides: dict[str, bool] | None = None`, applied at line 148-149.
`grep` finds **no caller anywhere**, production or test. It is a parameter whose only purpose is to
let something force a "non-negotiable" check to pass — the exact seam R5 exists to prevent, built
speculatively.

**T-108 — delete `deterministic_overrides`.** *Done when:* the parameter is gone and the tests still
pass (they do not use it).

---

### V-66 · P2 · Extraction reads the first 8 kB of a source and says nothing about it

`agents/extraction.py:85` — `raw_text = decoded_text[:8000]` goes to the model, while the verbatim
check at line 127 runs against the **full** `decoded_text`. Soundness is preserved (a quote must
still appear in the document), but for any source longer than 8 kB the claims come from a prefix and
nothing records that: no log line, no field on the Snapshot, no note in provenance. An `Evidence`
row's locator can name a section the model never saw.

**T-109 — record the truncation, or chunk the source.** *Done when:* the extracted window is either
the whole document or is recorded on the Snapshot/ModelCall row, and a test asserts it for an
oversized source.

---

### V-67 · P2 · The story-angle call is made even when there is nothing to write about

`agents/script.py:68` —
`verified_claims_summary="\n".join(claims_summary) or "Archival primary source records."`

With zero verified claims the model is handed a placeholder sentence instead of evidence, produces an
angle grounded in nothing, and **only then** does `generate_script` raise `UnsupportedClaimError`
(line 122). One paid Tier 2 request is spent to reach a failure that was knowable before the call —
on a budget ADR-0012 measures at 20 a day.

**T-110 — check for verified claims before the angle call, and delete the placeholder.**

---

### V-68 · P2 · A short embedding batch silently drops beats from the storyboard

`agents/storyboard.py:62,66` use `zip(..., strict=False)` for `(script.beats, beat_embs)` and
`(candidates, candidate_embs)`. If the embedder returns fewer vectors than inputs — a truncated
Ollama response, a batch limit — the extra beats are **silently omitted from the storyboard**, so the
rendered video is missing beats the approved Script contains, with no error.

**T-111 — `strict=True`, or an explicit length check that raises.**

---

### V-69 · P3 · A rejected fabricated quote is logged verbatim and counted nowhere

`agents/extraction.py:148-152` logs `quote=ev_item.quote` when a quote fails the verbatim check —
writing the model's invented sentence into the log stream, and recording the fabrication attempt
**only** there. No counter, no column, no metric. "The model invented six of eight quotes" is
invisible to every measurement Atlas takes, which is precisely the signal T-36's golden set needs.

**T-112 — count rejected quotes on the ModelCall or Snapshot row.** Fold into **T-36**.

---

### Checked on the second pass and found clean — do not re-audit

- **`ExtractedLinkItem.claim_index` and `evidence_index` both carry `ge=0`** (`agents/models.py:39-40`),
  so a negative index cannot wrap around and mis-link evidence to the wrong claim.
- **`claim_versions` has primary key `(claim_id, version)`** and `knowledge_object_versions` has
  `(ko_id, version)`. Append-only versioning is enforced by the database; a concurrent
  `save_claim` collides with an `IntegrityError` rather than duplicating a version.
- **`ScriptBeatItem.claim_ids` has `min_length=1`** — Invariant 1 is enforced at the schema, not only
  at the backstop.
- **`LocalStorage`** validates keys against a strict `sha256/xx/yy/<64 hex>` pattern, resolves and
  prefix-checks the path, and writes atomically via `mkstemp` + `os.replace`. No path traversal.
- **`LoggingNotifier`** nests the payload under one key, which is the correct fix for V-01.

---

## 3. Angle 2 — Security

**Deployed posture, established first as §18.3 requires:** `Settings.api_auth_enabled` defaults to
**`False`** (`packages/atlas/src/atlas/platform/config.py:88-90`). `docker-compose.yml` sets no
`ATLAS_API_AUTH_ENABLED` and publishes Caddy on **`:80` and `:443`** proxying straight to the API.
So the shipped deployment is an **unauthenticated write API**, and one of those writes runs the
pipeline and spends the Gemini key.

### V-29 · P0 · Auth "enabled" with no key configured accepts any key

`apps/api/dependencies.py:46-58`:

```python
if settings.api_auth_enabled and (
    not api_key or (settings.api_key and api_key != settings.api_key)
):
    raise HTTPException(401, ...)
```

If `ATLAS_API_AUTH_ENABLED=true` and `ATLAS_API_KEY` is unset, `settings.api_key` is `None`, the
right-hand clause is falsy, and the condition collapses to `not api_key`. **Any non-empty
`X-API-Key` value authenticates.** The operator who turns auth on and forgets the key gets a
green-looking 200 and no protection.

Second defect in the same expression: `api_key != settings.api_key` is a non-constant-time
comparison. Use `secrets.compare_digest`.

**T-78 — fail closed.**
*Done when:* enabling auth without a key raises at startup (or rejects every request), the comparison
is constant-time, and three tests cover: auth off → 200; auth on + no configured key → refused; auth
on + wrong key → 401.

---

### V-30 · P0 · Every write route is reachable with no credential, by default

**Measured.** The probe sent no `X-API-Key` header at all and every write was processed:

```
POST /domains (no X-API-Key) -> 409     # 409 = the use case ran and refused a duplicate
POST /topics                 -> 409
POST /channels               -> 409
POST /runs unknown topic     -> 404     # reached CreateRunUseCase
```

`POST /runs` then executes eighteen stages inside the request (V-19), and stage 1 calls Gemini for
real. On a free tier the audit measures at **20 requests a day**, an unauthenticated caller can
exhaust the budget with a handful of requests — and quota scarcity is the documented root cause of
the 2026-08-29 fabrication incident (`AUDIT-2026-08-29.md` §4, ADR-0012 context).

There is also no rate limit of any kind on the HTTP surface.

**T-79 — decide and document the deployment posture, then enforce it.**
*Done when:* `docker-compose.yml` sets `ATLAS_API_AUTH_ENABLED=true` with a key from the environment
(or the Caddyfile terminates auth), `ARCHITECTURE.md` §10 states the posture, and the default for a
container image is *closed*. Note that T-57 (the two routes with no dependency) is a subset of this
and should close in the same change — the dashboard already sends the header on every request, so it
will not break (confirmed below).

---

### V-31 · P1 · No length or format validation on any identifier or free-text field

`apps/api/schemas.py` declares every ID as a bare `str` with no `max_length` and no pattern
(`CreateDomainRequest.id:110`, `CreateTopicRequest.id:138`, `CreateChannelRequest.id:158`), and
`style_profile: dict[str, Any]` (`schemas.py:163`) accepts arbitrary nested JSON of any size.

**Measured:**

```
POST /domains 5000-char id     -> 500 {"error":"InternalServerError","message":"An unexpected server error occurred"}
POST /domains slash+newline id -> 201 {"id":"a/b\nc","name":"n","description":"d", ...}
```

Two distinct problems.

1. **The 5 kB ID reaches Postgres** and dies on `varchar(64)` with
   `StringDataRightTruncationError`. The response body is correctly generic, but
   `apps/api/main.py:222-231` logs `error=str(exc)`, and for a SQLAlchemy `DBAPIError` that string
   contains the full `INSERT` statement **and every bound parameter**, including the 5 kB payload.
   This is the same log-leak §18.3 flags from V-16's 500, still present for any untyped exception.
   Today the parameters are IDs and titles; the rule (**R12**) is about the shape, not today's
   contents.
2. **`"a/b\nc"` is accepted and persisted** — 201 Created. The structured log line reads
   `domain.created domain_id='a/b\nc'`. A newline inside a log field is log injection; a slash inside
   an ID breaks the first path-parameter route anyone adds (`GET /domains/{id}`); and the value is
   echoed verbatim into JSON responses and into the dashboard.

**T-80 — constrain the identifier type once, at the boundary.**
*Done when:* a single annotated `EntityId` type (`max_length=64`, `pattern=^[a-z0-9_]+$` or whatever
`GLOSSARY.md` decides) is used by all four create schemas; free-text fields carry `max_length`;
`style_profile` and any future `research_profile` carry a size cap; the catch-all handler logs
`exc.__class__.__name__` and a redacted message rather than `str(exc)`; and tests cover an over-long
ID (422, not 500) and a newline ID (422, not 201).

---

### V-32 · P1 · `actor_id` — including on an approval — is whatever the client says it is

`ApproveGateRequest.actor_id` (`schemas.py:70`), `RejectGateRequest.actor_id` (`schemas.py:88`),
`CreateFocusRequest.actor_id` (`schemas.py:187`), `CreateRunRequest.actor_id` (`schemas.py:24`) all
default to `"operator"` and are taken straight from the request body. `verify_api_key` returns the
key (or `"anonymous"`) into a parameter named `_auth` that every route discards.

`ExecutionRepository.record_approval` writes that string into `approvals.actor_id`, and
`PipelineRunner._asset_selection_was_approved_by_a_human` (`runner.py:408-423`) reads those rows to
satisfy **Invariant 9**. So the record that proves a human approved AI imagery carries a
self-declared name, on an API that is unauthenticated by default.

Nothing here is a bypass of the gate itself (**R5 holds** — there is no auto-approve path, no `--yes`
flag, and no loop over the `gates` table anywhere in the tree). The defect is attribution, not
authorisation.

**T-81 — derive the actor from the credential, not the body.**
*Done when:* `verify_api_key` returns a principal, the gate routes use it, `actor_id` is removed from
`ApproveGateRequest`/`RejectGateRequest`, and a test asserts the recorded actor is the authenticated
one and not the body's.

---

### V-33 · P2 · A default API key is compiled into the browser bundle

`apps/web/src/api/client.ts:25`:

```ts
const API_KEY = import.meta.env.VITE_API_KEY || 'atlas-dev-key';
```

Two things. The literal `'atlas-dev-key'` ships in `dist/assets/index-*.js` and, against a server
with V-29's bug, authenticates. And a *real* `VITE_API_KEY` would be inlined by Vite into a public
bundle — a browser SPA cannot hold a server credential.

**T-82 — decide how the dashboard authenticates.**
*Done when:* either the browser holds no key (Caddy or a session cookie in front), or the fallback
literal is removed and `ARCHITECTURE.md` §10 records that `VITE_API_KEY` is public by construction.

---

### V-34 · P2 · A database password is committed

`docker-compose.yml:6` `POSTGRES_PASSWORD: atlas_password`, repeated verbatim in the `api` and
`worker` connection URLs (lines 31, 52). CLAUDE.md forbids secrets in code and fixtures. It is a
local development password, which is why this is P2 and not P0 — but the same file is the deployment
description, so the password is also the deployed one.

(`.github/workflows/ci.yml:22` has the same shape for the ephemeral service container. That one is
conventional; note it, do not chase it.)

**T-83 — read the password from the environment with no default.** *Done when:* `docker compose
config` fails, or refuses to start, without `POSTGRES_PASSWORD` set.

---

### Second pass — the fetcher, the prompt loader and the backup tool

### V-71 · P0 · Source text is interpolated raw into the extraction prompt

`prompts/claim_extraction_v1.txt:18-22` fences the source between `"""` markers.
`agents/extraction.py:87-94` passes `raw_text` — bytes fetched from an arbitrary URL — with **no
neutralisation of the fence, no escaping, no instruction hierarchy**.

A page containing `"""` followed by instructions closes the fence and issues its own task. The
extraction agent writes whatever comes back as Claims and Evidence, and the verbatim guard
(`extraction.py:127`) **passes**, because the injected "quote" really is present in the document the
attacker controls.

Chain it: injected claim → **V-58** promotes it on a `"verif"` substring or a missing field →
`_assert_script_claims_are_traceable` sees `VERIFIED` with an evidence chain → beat → render. A
hostile web page can put a fabricated fact through every layer of Invariants 1 and 2 with the
traceability chain intact.

Reachability is not theoretical: **V-70** below means the URL fetched need not even come from a
search result.

Atlas's entire thesis is that facts come from sources rather than from a model. This is the one
attack that inverts that, and there is no mitigation in the tree — no delimiter escaping, no
"treat the following as data" framing, no post-hoc check that a claim's text is grounded in the
snapshot rather than merely that its quote is.

**T-113 — treat source text as data, and prove a claim is grounded.**
*Done when:* the source block is escaped or delimited with a nonce the source cannot contain, the
prompt states that content between the delimiters is data and never instructions, and a test feeds a
snapshot containing a fence-break plus an injected instruction and asserts no claim from the
injection reaches the Knowledge Object.

---

### V-70 · P1 · The source fetcher is an unrestricted SSRF primitive

`adapters/sources/fetcher.py:39-55`. `httpx.AsyncClient(follow_redirects=True)` then
`client.get(url)` with:

- **no scheme allowlist** — whatever `SearchResultItem.url` holds;
- **no host or IP filtering** — `http://127.0.0.1:11434` (the Ollama daemon), `http://localhost:8000`
  (Atlas's own API), `http://169.254.169.254/…` (cloud metadata) are all in range;
- **redirects followed blindly**, so an allowlisted host can hand off to an internal one;
- **no response size limit** — `response.content` reads the whole body into memory in the same
  process that serves HTTP and runs the pipeline, then writes it to disk.

The URL comes from the search adapter's response or, when search returns nothing, from the fabricated
fallback in **V-81**. Whatever comes back is snapshotted and becomes evidence.

**T-114 — allowlist the scheme, block private and link-local ranges, cap the body, re-check after
every redirect.** *Done when:* a test asserts `http://127.0.0.1/…` and a redirect to a private
address are both refused with a typed error, and a body over the cap is refused rather than buffered.

---

### V-72 · P2 · `render_prompt` substitutes into already-substituted text

`prompts/loader.py:74-78` loops over kwargs in call order, substituting each into the running result.
A value inserted early is re-scanned for the placeholders of values inserted later. `topic_title` is
substituted first and `source_text` last, so a Topic **title** of `{{ source_text }}` — settable
through the unauthenticated `POST /topics` — expands into the source body.

Low impact on its own; it is the same class as V-71 and should be fixed in the same change: build the
output in one pass from a mapping, never by repeated substitution.

Fold into **T-113**.

---

### V-73 · P1 · The backup tool puts the database password in argv and in its error message

`apps/cli/main.py:452` and `:485`:

```python
sync_db_url = settings.database_sync_url.replace("+psycopg", "").replace("+asyncpg", "")
subprocess.run(["pg_dump", sync_db_url, "-F", "c", "-f", "/tmp/db_dump.custom"], check=True)
...
except (subprocess.CalledProcessError, OSError) as e:
    console.print(f"[bold red]Backup failed: {e}[/bold red]")
```

Three problems.

1. **The URL is an argv element**, readable by any local user via `ps`. In the deployed configuration
   that URL is `postgresql://atlas:atlas_password@postgres:5432/atlas_db` (**V-34**).
2. **`CalledProcessError.__str__` includes the full command**, so a failed backup prints the password
   to the console — **R12** ("secrets never enter a URL, a log, or an error message") broken by the
   tool **R11** depends on.
3. **The dump is written to a fixed `/tmp/db_dump.custom`** and never removed. A full database dump
   left world-readable on a shared host after every backup. `restore` extracts an untrusted tar into
   `/tmp` and then `cp -r`s from it.

**T-115 — pass credentials in the environment, redact the error, use a private temp dir.**
*Done when:* `PGPASSWORD`/`PGSERVICEFILE` or a `.pgpass` carries the credential, the except block
prints `e.returncode` and a redacted command, the dump goes to a `mkdtemp(mode=0o700)` that is
removed in a `finally`, and a test asserts the printed failure contains no password.

---

### V-74 · P2 · A dead second backup implementation that does not back up the database

`apps/cli/backup_restore.py` defines its own Typer app with `backup`/`restore`. It is **never
registered** — `apps/cli/main.py` adds six sub-apps and not this one, and `pyproject.toml`'s only
entry point is `apps.cli.main:app`. Its `backup` docstring says "Backup Postgres database and blobs"
and it runs **`tar -czf … -C /var/atlas blobs`** — no `pg_dump` at all — then prints "Backup
complete!" and **exits 0 on failure**.

The registered commands in `main.py` are correct; this is a wrong copy sitting beside them.
CLAUDE.md: "Never introduce a second way to do something that already has a way."

**T-116 — delete `apps/cli/backup_restore.py`.**

---

### Security items checked and found clean — do not re-audit these

- **`.env` is untracked and ignored** (`git check-ignore -v .env` → `.gitignore:2`; `git ls-files`
  has no entry). It holds seven live provider keys, four of which (`GROQ`, `MISTRAL`, `NVIDIA`,
  `OPENROUTER`) belong to providers Atlas does not use — `Settings` ignores them (`extra="ignore"`).
  Blast radius worth knowing; not a code defect.
- **R12 in the provider adapters holds.** `GeminiLlm` sends the key in the `x-goog-api-key` header,
  never in the URL (`adapters/llm/gemini.py:67`), and every error path runs through
  `_redact_error` → `platform/redaction.py`. Covered by
  `tests/unit/test_no_fabrication.py:339` and `:366` (Gemini and Freesound).
- **No shell injection in the renderer.** `subprocess.run` with an argument list, no `shell=True`,
  numeric interpolations only.
- **The web client sends `X-API-Key` on every request**, including `/runs/{id}/steps` and
  `/runs/{id}/gates` (`client.ts:29-31`, one `request()` helper). **Closing T-57 will not break the
  dashboard** — §18.3 asked; this is the answer.
- **CORS** is `settings.cors_origins` (four localhost origins) with `allow_credentials=True`. Correct
  for the dev posture; revisit with T-79.

---

## 4. Angle 3 — Experience

### V-35 · P1 · A failed pending-gates fetch is shown as "No pending Gates"

`apps/web/src/App.tsx:32-35` destructures only `data` from the gates query and discards `error`. The
value flows to three places: `Header.pendingGatesCount` (the badge), `RunSummary.pendingGates` (the
tile "Awaiting a human"), and `ApprovalQueue.gates`.

When `GET /gates/pending` fails, `gates` is `[]` and the operator sees a **zero badge**, a tile
reading **"Awaiting a human: 0 — Gates suspended for an operator decision"**, and
`ApprovalQueue.tsx:76` **"No pending Gates"**. Nothing on screen says the request failed. Compare
`runsError`, which *is* rendered (`App.tsx:63-67`).

An operator concluding "nothing is waiting for me" from a failed request is R13 broken at the surface
R13 exists for.

### V-36 · P1 · A failed topics fetch is shown as "Topics: 0"

`apps/web/src/components/RunSummary.tsx:29` runs its own `['topics']` query and renders
`value={(topics.data ?? []).length}` at line 36 — `topics.error` is never read. The component's own
header comment says "a count of zero is shown as zero (**R13**)". A zero produced by a *failure* is
rendered identically to a zero produced by an empty table.

**T-84 — no tile, badge or empty state may render a fetch failure as a fact.**
*Done when:* `App.tsx` surfaces the gates error the way it surfaces the runs error; `RunSummary`
renders a distinct state for `isError` on each tile it sources; and a Playwright assertion fulfils
`/api/gates/pending` and `/api/topics` with a 500 and asserts the failure is visible and the words
"No pending Gates" / a zero count are **not**.

The rest of the dashboard is in good shape and should not be re-audited: `CatalogManager` has a
`Failure` component per section plus a mutation-error banner (lines 69-75, 154, 175, 306, 413, 546),
distinct empty states per entity (246, 379, 476, 637), `FocusLauncher` renders `topics.error` (175)
and every mutation error (64, 76, 88, 100), `ApprovalQueue` reports a failed action as a failure
("Gate action failed, nothing was recorded", line 142), `RunPipeline` renders both query errors (126,
129), `KnowledgeExplorer` and `TelemetryStream` render theirs, and `Header` tracks `isError` on
health.

---

### V-37 · P2 · Nobody can set the Active Focus, so every Run captures a Focus with no row

`FocusRepository.set_active_focus` (`focus_repository.py:167`) has **no production caller**. Grep for
it returns only `tests/integration/*`. There is no CLI command (`apps/cli/main.py` registers
`run`, `gate`, `quota`, `domain`, `topic`, `channel` — no `focus`) and no HTTP route
(`ARCHITECTURE.md` §2.1 lists `GET`/`POST /focuses` and nothing else).

Consequence chain, all confirmed:

1. `CreateRunUseCase` (`create_run.py:67-69`) calls `get_active_focus()`, which returns `None`.
2. It falls through to `create_run.py:72-81`, which builds a `Focus` **in memory** with
   `generate_id("foc")` and **never persists it**.
3. `FocusSnapshot.from_focus` captures it into `runs.captured_focus`, so the Run names a `foc_…` ID
   with no row behind it.

This is not an edge case — with no way to set the pointer it is the **only** path. Live evidence from
the `atlas` database: `focus` **0 rows**, `active_focus` **0 rows**.

`CatalogManager.tsx:639` already tells the operator the truth ("A Run created now captures a default
Focus built in memory rather than…"), which is honest and is why this is P2 rather than P1.

§18.4 asked whether the fallback is acceptable. **It is not, for a different reason than expected:**
the fallback is unavoidable because the pointer has no setter. This is V-15's exact shape — a
repository method whose only caller is a fixture — surviving the T-62 sweep.

**T-85 — persist the fallback Focus and give the Active Focus pointer a setter.**
*Done when:* `POST /focuses/{id}/activate` (or `atlas focus activate`) exists and is in
`ARCHITECTURE.md` §2.1; `CreateRunUseCase` persists the Focus it invents before capturing it; and an
integration test asserts `runs.captured_focus.focus_id` always resolves to a `focus` row.

---

### V-38 · P2 · A Domain's Research Profile cannot be set through the API

`CreateDomainRequest` (`schemas.py:107-113`) has `id`, `name`, `description` — **no
`research_profile`** — and `apps/api/routes/domains.py:47-50` passes only those three, so
`CreateDomainUseCase`'s `research_profile` parameter is always `None` and every Domain created
through the dashboard gets `ResearchProfile()`. `GET /domains` returns the profile
(`domains.py:24-31`) and the Catalog tab renders it; the same module's docstring says the Research
Profile "is what makes it more than a tag".

Read-only for a field the UI displays, on the same route that creates it.

**T-86 — accept a Research Profile on create, or say the dashboard cannot author one.**
*Done when:* either `CreateDomainRequest` carries a validated `ResearchProfile` and §2.1 records it,
or `STATUS.md` §3 lists "no way to author a Research Profile" beside the Style Profile line that is
already there.

---

### V-39 · P2 · A rejected gate leaves the operator with no action

The consequence of V-21, stated from the operator's seat: after a rejection the Run reads `suspended`
in the Runs table, `GET /gates/pending` no longer returns its gate, the Approval Queue says "No
pending Gates", and the Pipeline tab shows the stage rows with no gate holding them. There is no
button, CLI command or route that moves the Run. Fold into **T-70**.

---

### V-75 · P1 · One unmodified keystroke approves a human gate

`apps/web/src/components/ApprovalQueue.tsx:55-67`:

```tsx
const handleKeyDown = (e: KeyboardEvent) => {
  if (['INPUT','TEXTAREA','SELECT'].includes((e.target as HTMLElement)?.tagName)) return;
  if (e.key === 'a' || e.key === 'A') { e.preventDefault(); void handleApprove(); }
  else if (e.key === 'r' || e.key === 'R') { e.preventDefault(); setShowRejectModal(true); }
};
window.addEventListener('keydown', handleKeyDown);
```

Pressing **`a`** anywhere outside a form field calls `approveGate` immediately — no modifier, no
confirmation, no undo. It writes an `Approval` row indistinguishable from a considered decision, and
on an asset-selection gate that row is the whole of Invariant 9's evidence that a human approved
AI-generated imagery.

**The asymmetry is backwards.** `r` opens a modal that demands a target, a rubric dimension and a
written reason before anything is sent. Rejection is guarded; approval is one letter.

Invariant 9: "explicit human approval. No exceptions, no auto-approve flag, no bypass." R5:
"Automate the operator UI, never the decision." A single keystroke with no confirmation is not the
explicit act either rule describes, and it is the one action in Atlas that cannot be taken back.

The button label advertises it ("Approve & Resume (A)"), so this was deliberate — which makes it a
decision to revisit rather than an oversight, and it should be revisited in writing.

**T-117 — the approve shortcut needs a deliberate act.**
*Done when:* the bare `a` binding is removed or requires a modifier plus a confirm step, the
rejection path stays as it is, and `DECISIONS.md` records the choice against Invariant 9.

---

### V-76 · P2 · The rejection modal promises a rework cycle that does not exist

`apps/web/src/components/StructuredRejectionModal.tsx:79-80`:

> "Feedback is stored on the Approval row and drives the rework cycle."

The first half is true. The second is false — **V-21** establishes that nothing consumes the feedback
and no stage re-runs. The operator is told their critique will drive a regeneration that will never
happen.

R13: every line a human reads comes from the system as it is, not as it was designed. Fix the copy in
the same change as **T-70**, whichever way that decision goes.

---

### What §18.4 asked that this session could not finish

**The empty-database walkthrough (T-64's own *Done when*) is still not done.** It needs a browser
against a live API on a freshly migrated, unseeded database, and migration `0001_initial_schema`
seeds four Domains and three Channels, so "empty" means dropping those seeds or using a database
where they were removed. Blocked on nothing but time. Two things this session established that will
shape it:

- With no Focus rows, the picker shows the "No Active Focus" note and V-37's unpersisted Focus is what
  a Run will capture.
- With no auth, no key is needed to drive it.

**T-87 — the empty-database walkthrough, in a browser, written up.** *Done when:* a fresh database
(migrated, seeds removed) is taken from zero to a suspended Run entirely through the dashboard, with
every dead end named, and T-64's box in §6 is ticked or a residual task is opened.

---

## 5. Angle 4 — Functionality: documents against code

### V-40 · P0 · ADR-0012 is Accepted and five of its six parts do not exist

ADR-0012 ("Tier 1 becomes the primary inference tier") is `**Status:** Accepted`, dated 2026-08-29.
Its four supporting requirements are stated as "prerequisites and not follow-ups". Checked one by one
against the tree today:

| ADR-0012 says | Code says | File |
|---|---|---|
| Claim extraction, story angle, script writing, quality judging move to **Tier 1 / ollama** | all four still `tier=2, provider="gemini"` | `application/policies/quota_policy.py:74-119` |
| `GeminiLlm.capabilities` must state the real limit, **20 rpd**; `rpd_limit=1500` is "fabricated" | `rpd_limit=1500` | `adapters/llm/gemini.py:52` |
| — and the enforced budget with it | `DEFAULT_PROVIDER_LIMITS["gemini"]["rpd"] = 1500`, `"rpm": 15` | `platform/quota.py:28-33` |
| `gemini-2.0-flash` is **retired**; the API returns `404: no longer available` | still the default model ID in the adapter **and** in five routes | `adapters/llm/gemini.py:39`; `quota_policy.py:54,78,86,94,102` |
| The container must wire a **Tier 2 → Tier 1 fallback with backoff**, recorded in provenance | no retry, no backoff, no fallback anywhere (`grep -rn "backoff\|retry" packages apps` → one docstring) | `adapters/llm/gemini.py:100-104` |
| **Model IDs move to config**; none may be a default argument or a policy literal | both, still | as above |
| Ollama base URL moves to settings | **done** (D116) | `platform/config.py:66-70` |

Plus: `OllamaLlm` — the Tier 1 adapter the whole ADR turns on — is one of the five orphans
(`STATUS.md` §4, T-28). It is reachable from nothing.

**The operational consequence is the one that matters.** The first real-provider call Atlas makes
will be `POST .../models/gemini-2.0-flash:generateContent`, and ADR-0012 records, from a measurement
against the live key, that this returns **404**. `T-34` cannot succeed until this is fixed, and
`QuotaManager` will happily authorise 1500 requests against a 20-request budget in the meantime.

`STATUS.md` §4 registers exactly one of these seven rows ("Model IDs are hardcoded. ADR-0012 §3;
defect C-08"). `SPEC.md` §17.4 records that ADR-0012 amends §11 without recording that the amendment
was never applied. **This is the §18 thesis in one finding: the register only ever contained what
somebody already knew.**

**T-29 and T-30 already exist for this** (§15.9 positions 10 and 11) but are described as
configuration work. Re-scope them:

**T-29 (re-scoped) — make the declared limits the measured limits and move model IDs to config.**
*Done when:* `rpd`/`rpm` for gemini come from `Settings` and default to the measured free-tier
numbers; no model ID is a literal in an adapter or a policy; a test asserts `QuotaManager` refuses
call N+1 at the configured daily limit.
**T-30 (re-scoped) — apply ADR-0012's routing table and wire `OllamaLlm`.**
*Done when:* the four task kinds route to tier 1, `Container` resolves an `OllamaLlm` for them,
`GeminiLlm` is reached only by `VERIFICATION`, and a test asserts `RoutingPolicy` matches ADR-0012's
table row for row so the next divergence fails the suite.
**T-88 — the Tier 2 → Tier 1 fallback with backoff, recorded in provenance.**
*Done when:* a 429 or 5xx from Gemini retries with backoff and then falls back, and the resulting
`model_calls` row names the provider and model that actually answered (Invariant 7).

---

### V-41 · P1 · The Research Profile has no reader — SPEC §9's source policy is not enforced

`grep -rn "research_profile\|source_tier_floor\|source_allowlist\|preferred_apis"` over `packages`
and `apps`, excluding tests, returns **only**: the Pydantic model
(`domain/focus/models.py:39-45,62`), the migration seed
(`alembic/versions/0001_initial_schema.py:544-611`), the column
(`persistence/tables.py:367`), the repository round-trip (`focus_repository.py:41-68`), the create
use case's parameter (`create_domain.py:26,41`), and the API serializer (`routes/domains.py:29`,
`schemas.py:133`).

**No agent, no policy and no adapter ever reads a value out of it.** `ResearchAgent.execute` takes
`topic_id`, `search_query`, `limit` — no Domain, no profile
(`runner.py:463-472`). So `source_tier_floor: "primary"` on `dom_history` constrains nothing; the
allowlist filters nothing; `preferred_apis` selects nothing. Everything goes through
`WikipediaSearch` with the query `f"{topic_title} primary history archive"` and `limit=1`.

This also reframes **V-17**: the incident that "weakened a real Domain's `source_tier_floor` from
`primary` to `institutional`" damaged a field with no consumer. That is worth writing down, because
the duplicate guard was built to protect it.

**T-89 — enforce the Research Profile, or record that SPEC §9 is unimplemented.**
*Done when:* either `ResearchAgent` receives the Domain's profile and a test proves a source below
the tier floor or outside the allowlist is rejected, or `SPEC.md` §17.4 gains a row saying the source
policy is declared and unenforced, and `STATUS.md` §3 lists it.

---

### V-42 · P1 · The Focus changes nothing about what Atlas produces

`run.captured_focus` is read at exactly two points in the pipeline:

- `runner.py:217` — the `focus_id` string inside the idempotency `input_hash`.
- `runner.py:458-460` — `topic_agent.execute(run.captured_focus, ...)`, at stage 1, **whose output
  is counted and discarded** (`return f"ideas_count_{len(ideas)}"`).

Every later stage keys off `topic_title`. So SPEC §5 — "Focus — the operator's control surface" — and
ADR-0002's scope modes, facets and hard/soft/exploratory semantics have **no effect on any artifact
Atlas produces**. `ScopeMode` is stored, serialised, displayed in the picker, and never consulted.

Invariant 6 ("no hidden global mutable state; runs capture their configuration by value") holds
structurally, as `STATUS.md` §2 says. What does not hold is that the captured value is used.

**T-90 — thread the Focus into research and script generation, or say it is inert.**
*Done when:* either the Focus's facets and scope mode reach at least the research query and the
script prompt, with a test asserting two different Focuses produce different queries, or `SPEC.md`
§17 gains a row and `STATUS.md` §3 lists "the Focus does not affect any stage after 1".

---

### V-43 · P1 · The per-minute token limit is never checked

`platform/quota.py:66-88`. `check_rate_limits` compares `minute_requests` to `rpm`, `daily_requests`
to `rpd`, and `daily_tokens + estimated` to `tpd`. **`tpm` is never read**, and neither is
`minute_tokens`. The limit is declared for all three providers
(`DEFAULT_PROVIDER_LIMITS`, lines 26-44) and enforced for none.

**T-91 — check `tpm`, or delete it.** *Done when:* either the minute-token window is enforced with a
test that trips it, or the key is removed from the limits table so nothing reads as enforced that is
not.

---

### V-44 · P1 · A failed provider call is never metered

Every agent follows the same shape — `topic.py:43-64` is representative:

```python
await self.quota_mgr.check_rate_limits(route.provider)   # before
extracted = await self.llm.extract(request, ...)          # may raise
await self.quota_mgr.record_invocation(...)               # only on success
```

`GeminiLlm.extract` raises `GeminiProviderError` on a 429, a 5xx, a timeout, or malformed JSON
(`adapters/llm/gemini.py:170-173`). The request was issued and **counted by the provider**; Atlas
writes no `model_calls` row and no `quota_ledger` row. On a 20-request daily budget, a run that fails
twice at stage 4 has spent three requests and recorded one.

Compounded by **V-20**: even the successful meterings are rolled back when a later stage fails.

Invariant 8 says "every model call is metered against the quota ledger **before** it is made". The
check is before; the ledger write is after, and conditional.

**T-92 — meter the attempt, not the success.**
*Done when:* the ledger row is written for a call that raises, with `outcome` naming the failure
(`ModelCall.outcome` already exists and is always `"success"` today), and a test asserts a failed
provider call still consumes budget.

---

### V-45 · P2 · ADR-0001's operational half does not exist

ADR-0001's Consequences require "retry, backoff, dead-lettering, lease expiry, and stuck-Run
detection" and "a reaper process … to expire abandoned leases and surface Runs stuck in `running`".

```
$ grep -rn "reaper\|stuck\|dead.letter\|backoff\|retry" --include=*.py packages apps | grep -v test
packages/atlas/src/atlas/domain/execution/models.py:137:    """One stage within a Run, individually retryable and checkpointed."""
```

One docstring. Also unbuilt from the same ADR: transactional enqueue (`create_run` flushes, then
`enqueue` no-ops), `SKIP LOCKED` claiming, and re-enqueue on resume — `DramatiqQueueBroker.enqueue`
drops its `step_name` argument entirely (`adapters/queue/dramatiq_broker.py:11`), so a resume could
not name where to resume from.

Two more notes for **T-67**: `acquire_lock`'s TTL is 60 s (`runner.py:588`) which no real render
fits, and because the whole Run executes in one uncommitted transaction, the lease row is invisible
to other processes until the Run ends — so the lease provides no cross-process exclusion during the
work it is meant to protect. Fixing V-20's transaction boundary is a prerequisite for the lease
meaning anything.

**Fold into T-67**, and record the list so the ADR is either built or superseded as a whole.

---

### V-46 · P2 · Nothing asserts the routing table and the wired adapter agree

`check_rate_limits(route.provider)` reads the budget the **policy** names;
`record_invocation(provider=extracted.provider)` writes the budget the **adapter** reports. They agree
today only because `Container` wires one LLM and six of the seven used routes say `"gemini"`.

`TaskKind.ENTITY_EXTRACTION` says `provider="ollama"` (`quota_policy.py:66-73`) and has **no caller**,
so the mismatch is latent — until T-30 changes the table, which is exactly when it stops being
latent.

**T-93 — assert the route's provider is the provider that answers.** *Done when:* a test resolves
`Container`, walks `RoutingPolicy.DEFAULT_ROUTES`, and asserts each used route's provider matches the
adapter that would serve it.

---

### V-47 · P2 · The publishing schedule has no production caller

`PublishingRepository.save_window`, `get_windows`, `save_blackout_rule`,
`get_active_blackout_rules` — grep returns only `tests/integration/test_publishing_repository.py`.
`PublishScheduler` is an orphan (`STATUS.md` §4, T-28). The `publishing_windows` and `blackout_rules`
tables are seeded by migration `0001` and read by nothing.

So **ADR-0007** (publishing schedule and time zones) — four clocks, windows, the 22:00–06:00
audience-local blackout — is entirely unbuilt, not partially. `SPEC.md` §17.2's publish row records
"the stage does not consult `PublishScheduler` or the blackout rule" but not that the whole ADR has
no reader.

**Fold into T-21**, and note it in `SPEC.md` §17 as an ADR-0007 row rather than a publish-stage
caveat.

---

### V-48 · P2 · The impact index is never written

`SourceRepository.record_claim_usage` (`source_repository.py:326`) — grep returns only
`tests/integration/test_claim_impact_index.py` and
`tests/integration/test_knowledge_repository_acceptance.py`. **No stage records a claim usage**, so
`claim_usages` is empty for every Run and "which renders used this claim" — the retraction story
Invariant 4 and SPEC §12 exist for — cannot be answered.

`STATUS.md` §3 says "Graph, novelty check and impact index **beyond `claim_usages`** are not
implemented", which reads as though `claim_usages` works. The table exists; the writer does not.

**T-94 — record a claim usage per beat at render, or correct STATUS §3.** *Done when:* either
`REMOTION_RENDER` writes one `claim_usages` row per (claim, render, beat) and the e2e test asserts
them, or `STATUS.md` §3's sentence is rewritten to say the impact index has no writer.

---

### V-77 · P1 · Four of ADR-0002's seven decisions are unbuilt, including one that inverts

ADR-0002 was not read on the first pass. Its Decision section has seven numbered points; four do not
hold.

| ADR-0002 says | Code |
|---|---|
| 3. "Field is a policy selector… a Domain row carrying a Research Profile: source allowlists, preferred APIs, vocabulary, disambiguation hints. **This is what makes the second input earn its place.**" | Nothing reads it (**V-41**). The ADR's stated justification for the Domain concept is unimplemented. |
| 4. "Note resolves to a canonical Entity… resolved against Wikidata, scoped by the Domain… Ambiguity is surfaced for operator confirmation, never guessed." | **No Wikidata resolution exists.** `save_entity` has no production caller; `entity_id` is an optional free string the operator types (`CreateTopicRequest.entity_id`). No disambiguation, no confirmation flow. |
| 5. "Scope Mode… `hard` never leaves the Focus; `soft` prefers it; `exploratory` treats it as a seed." | `ScopeMode` is stored, serialised and displayed. **No stage reads it** (**V-42**). All three modes behave identically. |
| 6. "Precedence for new Runs: explicit arguments → Active Focus → **Channel default**." | `CreateRunUseCase` does explicit → Active Focus → **an unpersisted in-memory invention** (**V-37**). There is no Channel default; `Channel` carries a Style Profile and no Focus. |
| 7. "**Auditable.** Focus creation and Active Focus changes are **append-only** records with actor and timestamp." | `FocusRepository.set_active_focus` (`focus_repository.py:171-181`) runs `DELETE FROM active_focus WHERE id='default'` and then inserts. **The history of Active Focus changes is destroyed on every change.** |

Point 7 is the one that inverts rather than merely missing: an ADR promising append-only auditability
is implemented as delete-then-insert, in a system whose fourth invariant is "knowledge is
append-only".

**T-118 — reconcile ADR-0002 with the code, point by point.**
*Done when:* each of the four rows is either implemented or recorded in `SPEC.md` §17 and
`STATUS.md` §3 as unbuilt, and `active_focus` becomes an append-only history with a current-pointer
read (the same shape `claim_versions` already uses) or ADR-0002 point 7 is superseded in writing.

---

### V-78 · P1 · Two of the five provenance fields Invariant 7 names are constants

Invariant 7: "Every artifact records how it was made — provider, model ID, **prompt version**,
parameters, **input version, code version**. 'Rebuild this exactly' must always be answerable."

```
$ grep -rn 'code_version=' --include=*.py packages apps | grep -v test
application/agents/judge.py:89:        code_version="phase-5-v1",
application/agents/extraction.py:119:   code_version="phase-5-v1",
application/agents/storyboard.py:121:   code_version="phase-5-v1",
application/agents/verification.py:97:  code_version="phase-5-v1",
application/agents/topic.py:59:         code_version="phase-5-v1",
application/agents/script.py:89,155:    code_version="phase-5-v1",
```

Every `model_calls` row in every database says `phase-5-v1`, whatever commit produced it.

`prompt_version` records a **name** (`"claim_extraction_v1"`), not a hash. Editing
`prompts/claim_extraction_v1.txt` changes behaviour and changes nothing in provenance.
`prompts/loader.py:54` defines `get_prompt_hash`, which computes exactly the missing value, and it
has **no production caller** — only a re-export and a unit test asserting it is deterministic. R10's
shape: a function that exists instead of a check that runs.

`STATUS.md` §2 credits Invariant 7 as enforced, proven by
`test_model_call_provenance_matches_the_adapter_that_ran` — which asserts the **provider**. The claim
is narrower than the invariant.

**T-119 — record the code version and the prompt hash.**
*Done when:* `code_version` comes from the git SHA (or the package version) at one place rather than
seven literals, `ModelCall` carries the prompt hash from `get_prompt_hash`, and a test asserts that
editing a prompt file changes the recorded hash.

---

### V-79 · P1 · The sound design agent calls a rate-limited network provider with no quota manager

`agents/sound_design.py:11-13` — `SoundDesignAgent.__init__(self, sound_library: SoundLibrary)`.
**No `QuotaManager`.** `compose` calls `get_music_bed` once and `get_sfx` **twice per beat**
(`sound_design.py:20-43`), so a fifteen-beat script issues roughly thirty-one Freesound API calls,
none of them metered, none recorded in `model_calls` or `quota_ledger`.

Guard 9 (`test_no_fabrication.py:479`) asserts that every agent touching `self.llm` or
`self.embedder` holds a `QuotaManager`. A `SoundLibrary` is neither, so the guard passes. Invariant 8
says "Quota is a first-class resource… an unmetered call is a bug" — it does not say "model call
only", and ADR-0004 governs the whole provider ladder.

Separately, `get_sfx("keystroke")` is re-fetched inside the loop: fifteen identical lookups where one
would do.

**T-120 — meter the sound library, and widen Guard 9 to every provider port.**
*Done when:* `SoundDesignAgent` takes a `QuotaManager` and records each Freesound call, the
per-beat lookups are hoisted, and Guard 9 covers `sound_lib`, `search`, `source_fetcher`,
`image_search` and `image_gen` as well as `llm` and `embedder`.

---

### V-80 · P1 · Every source is recorded as Tier 0 PRIMARY, whatever it is

`agents/research.py:71-79`:

```python
source = Source(
    id=generate_source_id(), title=hit.title, url=HttpUrl(hit.url),
    author=hit.source_name,
    source_tier=SourceTier.PRIMARY,     # hardcoded, every time
    created_at=utc_now(),
)
```

Whatever the search returns — today a Wikipedia article — is persisted with `source_tier='primary'`.
The tier is not determined, it is asserted. Consequences:

- SPEC §9's source policy and the Domain's `source_tier_floor: "primary"` are satisfied **by
  construction** rather than by evidence, so **V-41**'s "the profile has no reader" is compounded: if
  it ever gained one, it would read a field that is always `primary`.
- `sources.source_tier` is a provenance field about a source that nothing established — R4's
  territory, in the database rather than in a fixture.
- The extraction prompt is handed `Tier: {{ source_tier }}` (`claim_extraction_v1.txt:16`), so the
  model is told the source is primary regardless.

**T-121 — derive the tier, or store `unknown`.**
*Done when:* the tier comes from the search adapter's knowledge of what it returned (or from the
Research Profile's classification), a Wikipedia hit is not `primary`, and a test asserts it.

---

### V-81 · P1 · When search finds nothing, the research agent invents a source

`agents/research.py:49-59`:

```python
if not search_hits:
    logger.warning("research.no_hits", ...)
    search_hits = [
        SearchResultItem(
            title=f"Archival Record for {topic_id}",
            url=f"https://en.wikipedia.org/wiki/{topic_id.replace(' ', '_')}",
            snippet=f"Primary encyclopedic source for {topic_id}.",
            source_name="Wikipedia",
        )
    ]
```

A hardcoded fallback payload, in a real agent, with an invented title, an invented snippet and a URL
**guessed from the Topic's slug** — `topic_origin_of_weapons` becomes
`https://en.wikipedia.org/wiki/topic_origin_of_weapons`, which does not exist. Whatever that URL
returns is fetched, snapshotted and recorded as a Tier 0 primary source (**V-80**).

This is exactly the shape **R1/R2** forbid — "no hardcoded response, canned payload… in any real
adapter" — living in `application/agents/` instead of `adapters/`, which is why no guard sees it
(**V-82**).

Also on this path: `except Exception as exc: logger.error(...); continue` (line 100) swallows every
fetch failure into a log line, contradicting CLAUDE.md's "errors are typed domain exceptions, never
bare `Exception`" — and by **V-20** that log line is the only trace, since the Run is rolled back.

**T-122 — no hits is a typed failure, not an invention.**
*Done when:* the fallback is deleted, empty search results raise a typed error the runner surfaces on
the Step, fetch failures raise rather than `continue`, and a test asserts a Run with no search hits
fails with a named reason instead of snapshotting a guessed URL.

---

## 6. Angle 5 — The end-to-end system, assuming every test lies

### V-49 · P0 · The migrated schema and the ORM models disagree, in 19 places

```
$ ATLAS_DATABASE_SYNC_URL=postgresql+psycopg://postgres@localhost:5432/atlas_test uv run alembic check
FAILED: New upgrade operations detected: [...]
```

Reproduced identically against **both** databases (`atlas` and `atlas_test`), both at head
`b1c4d7e90a25`. The material differences:

**Missing foreign keys — declared in the models, absent in the database:**

| Model declares | Database has |
|---|---|
| `GateTable.run_id → runs.id ON DELETE CASCADE` (`tables.py:570`) | `fk_gates_steps` only |
| `ApprovalTable.run_id → runs.id ON DELETE CASCADE` (`tables.py:608`) | `fk_approvals_gates` only |
| `ModelCallTable.run_id → runs.id ON DELETE CASCADE` (`tables.py:668`) | `fk_model_calls_steps` only |

Confirmed directly:

```
$ psql atlas_test -c "select conrelid::regclass, conname, contype from pg_constraint where ..."
 gates       | fk_gates_steps        | f
 approvals   | fk_approvals_gates    | f
 model_calls | fk_model_calls_steps  | f
```

A gate, approval or model call can name a `run_id` that does not exist, and deleting a Run does not
cascade to them.

**The index diffs are the opposite of what they look like — corrected on the second pass.** The
first pass read alembic's "Detected added index …" lines as missing hot-path indexes. They are not.
The migrations deliberately created **better composite indexes** than the single-column `index=True`
flags the models declare:

```
$ psql atlas_test -Atc "select indexdef from pg_indexes where indexname in (...)"
CREATE INDEX ix_quota_window       ON quota_ledger       (provider, window_type, window_start)
CREATE UNIQUE INDEX ix_steps_idempotency ON steps        (run_id, step_name, input_hash)
CREATE INDEX ix_pub_windows_lookup ON publishing_windows (channel_id, platform, content_format, day_of_week)
CREATE INDEX ix_model_calls_run_id ON model_calls        (run_id)
```

`get_quota_consumption_summary` filters `window_type` + `window_start` and groups by `provider` —
covered by `ix_quota_window`. `list_steps_for_run` and `list_model_calls_for_run` filter `run_id` —
covered. **There is no missing-index performance defect.** The correct fix for those nine diffs is to
**remove the redundant `index=True` flags from the models**, not to add indexes to the database.

The meta-finding survives the correction and is strengthened by it: the models are not the source of
truth they appear to be, the database is ahead of them, and the genuine drift below is buried in nine
lines of noise that nobody would read past.

**Type drift:** `model_calls.parameters` is `JSON` in the database, `JSONB` in the model.

**Name drift:** `ix_ko_versions_{entity_id,topic_id}` in the database vs
`ix_knowledge_object_versions_{...}` in the model.

**One diff is noise, and the fix is to change the model:** `uq_ko_version` on
`knowledge_object_versions(ko_id, version)` is declared at `tables.py:285` and is redundant — the
table's primary key is already `(ko_id, version)`. Uniqueness *is* enforced. Same for
`claim_versions`, whose PK is `(claim_id, version)` — **append-only claim versioning is safe**; only
a concurrent `save_claim` on one claim would collide, and it would surface as an untyped
`IntegrityError` → 500 (worth a line in T-71's scope, not its own finding).

**Why nothing caught it:** `tests/integration/test_alembic_migrations.py` runs
upgrade/downgrade/upgrade/downgrade and **asserts nothing** — it passes if no command raises. CI runs
`alembic upgrade head` and never `alembic check`.

**T-95 — one migration to close the drift, and `alembic check` in CI.**
*Done when:* `uv run alembic check` exits 0; a migration adds the three foreign keys and settles the
`JSON`/`JSONB` and index-name questions; the redundant `uq_ko_version` and the nine redundant
single-column `index=True` flags are removed from the models; `alembic check` is a step in `ci.yml`
**and** a test in the suite, so the next drift fails before it ships. Review the migration under
`backend-design:review-migration` discipline — adding an FK takes a lock and the tables are non-empty
in the `atlas` database.

---

### V-50 · P1 · No test in the suite ever commits

`tests/conftest.py:47-59`:

```python
async with session_factory() as session:
    yield session
    await session.rollback()
```

Every integration test — all 19 modules that use `db_session` — runs inside one transaction that is
rolled back. Nothing in the suite exercises: a commit, cross-transaction visibility, the
`with_for_update` row lock in `record_approval`, the `ON CONFLICT … WHERE expires_at <= now` lease in
`acquire_lock`, or **V-20's rollback**, which is invisible by construction because the fixture rolls
back anyway.

This is the structural reason the suite could be green while a failed Run left no trace.

**T-96 — one committing fixture, and use it for the durability tests.**
*Done when:* a `committed_session` fixture exists (truncating or dropping between tests), and at
minimum V-20's regression test, the GPU-lease concurrency test and the gate-lock test run on it.

---

### V-51 · P1 · The Compose `worker` still has V-18 — and so does `ATLAS_QUEUE_BROKER=dramatiq`

`grep -rn "set_broker"` finds exactly one call, in `tests/conftest.py:4`. Production configures no
dramatiq broker at all, and `redis` is not in `pyproject.toml` (only `dramatiq>=2.2.0`, line 19).

So `docker-compose.yml`'s `worker` service (`command: uv run dramatiq apps.worker.tasks`) imports
`apps/worker/tasks.py`, hits `@dramatiq.actor`, which calls `get_broker()`, which falls back to
Redis, which is not installed — **`ModuleNotFoundError: No module named 'redis'`**, at container
start. V-18 was routed around for the API and the CLI by defaulting to `InlineQueueBroker`; the
worker service and the `dramatiq` setting still walk into it.

`tests/integration/test_queue_broker_wiring.py:46` constructs `Container(queue_broker_kind="dramatiq")`
and asserts its type — it **never calls `enqueue`**, which is the line that raised. The regression
test for V-18 does not cover the configuration that reproduces V-18.

**T-97 — the `dramatiq` path must either work or refuse at construction.**
*Done when:* selecting `dramatiq` without a configured, reachable broker raises a typed error naming
what is missing, a test calls `enqueue` on that path and asserts it, and `docker-compose.yml`'s
`worker` service is removed or given a broker. Part of **T-67**; do not close T-67 without it.

---

### V-52 · P1 · The built dashboard has no deployment

`apps/web/src/api/client.ts:24` calls `/api/...`. The `/api` prefix is stripped by **the Vite dev
server only** (`apps/web/vite.config.ts:9-15`, `rewrite: path.replace(/^\/api/, '')`).

`docker-compose.yml` runs `postgres`, `ollama`, `api`, `worker`, `caddy` — **no service serves
`apps/web`**, and `Caddyfile` is a bare `reverse_proxy api:8000` with no static root and no `/api`
strip. If the built bundle were served from that origin, every request would arrive at the API as
`/api/runs`, which is not a route (the surface is `/runs`), and 404.

So `pnpm -r build` produces `apps/web/dist/` that nothing deploys, and the operator interface exists
only under `pnpm dev`. `ARCHITECTURE.md` §10 should say so.

**T-98 — serve the dashboard, or record that it is a development-only surface.**
*Done when:* either Caddy gets a static root for `apps/web/dist` and a `handle_path /api/*` that
strips the prefix before proxying (and `docker compose up` serves the dashboard), or
`ARCHITECTURE.md` §10 and `STATUS.md` §3 state that the built dashboard has no deployment path.

---

### V-53 · P2 · The browser tests never touch the API, and nothing checks the wire contract

All ten assertions in `apps/web/e2e/dashboard.spec.ts` install `page.route('/api/...')` handlers that
`route.fulfill(...)` synthetic JSON (first at line 17). No request reaches a server. They prove
exactly what T-55 built them for — that components render the response rather than a fixture — and
nothing about the API.

`STATUS.md` §2's phrase "renders **live API** topic IDs" overstates that; the IDs are live relative to
the component, not to the API.

The gap this leaves: **nothing anywhere asserts that `apps/api/schemas.py` and
`apps/web/src/api/types.ts` describe the same shapes.** V-03's root cause — a client typed against an
API that did not exist — is held off by hand-maintained agreement plus `ARCHITECTURE.md` §2.1. The
mocks themselves already drift: the run object at `dashboard.spec.ts:22-33` omits `captured_focus` and
`trace_id`, both required by `RunItem`.

**T-99 — pin the wire contract.**
*Done when:* either the TypeScript types are generated from `app.openapi()` in CI, or a test asserts
each response model's field set against `types.ts`, and the Playwright mocks are built from that
schema so a drifting mock fails.

---

### V-54 · P2 · The e2e caption assertion runs against a hardcoded literal

`tests/integration/test_pipeline_execution_e2e.py:314-316` asserts
`captions.startswith("WEBVTT")` and `"-->" in captions`, over `FakeRenderer`, whose captions are the
constant `b"WEBVTT\n\n00:00:00.000 --> 00:00:03.500\nKinetic Text Line"`
(`adapters/fakes/providers.py:398`). Deleting `generate_webvtt` from `StubRenderer` would not fail it.

**Not a hole, a mislabel:** the real derivation *is* covered, in
`tests/integration/test_production_adapters.py:140-145` and `:173-174`, which run `StubRenderer`
against real ffmpeg and assert `00:00:00.000 --> 00:00:02.000` and `PLACEHOLDER_CUE_TWO` from the
Timing Plan. `STATUS.md` §2's e2e sentence ("WebVTT captions carrying real cues") credits the wrong
test.

**T-100 — point the claim at the test that proves it.** *Done when:* `STATUS.md` §2 names
`test_production_adapters.py` for the caption derivation, and the e2e assertion either checks the
Timing Plan's cue text or is documented as a smoke check.

---

### V-55 · P3 · Test dependency overrides are never cleared

`tests/integration/conftest.py:45-96` mutates `app.dependency_overrides` on the module-level `app`
and returns the client with no teardown. Overrides persist after the test, bound to a `db_session`
that is closed. Harmless while every app-touching test uses the fixture; a trap for the first one
that does not.

**T-101 — clear the overrides in fixture teardown.** *Done when:* `api_client` is a yield fixture
that calls `app.dependency_overrides.clear()`.

---

### V-56 · P3 · Two hand-written rows in the application database are unrecorded

```
$ psql atlas -c "select id, title, created_at from topics order by created_at"
 topic_origin_of_weapons | The Origin of Weapons | 2026-09-05 10:03:44+05:45
 topic_origin_of_chess   | The Origin of Chess   | 2026-09-05 10:09:56+05:45
 topic_origin_of_art     | The Origin of Art     | 2026-09-05 10:59:54+05:45
```

`STATUS.md` §1 records **one** row written by hand — `topic_origin_of_weapons`. The other two are not
mentioned in `STATUS.md`, in `AUDIT-2026-08-29.md` §17, or in `DECISIONS.md`. The close-out checklist
item — "If you wrote a row to the local `atlas` database by hand, record what it was and whether it
overwrote anything (**R11**)" — was half-followed.

Nothing was destroyed (all three are additive, `status='proposed'`). It is a bookkeeping failure on
the rule that exists because of V-17.

**T-102 — record the two rows in STATUS §1.** *Done when:* §1 names all three and says which command
created them.

---

### V-57 · P3 · §18.1's test-module count is wrong

33 `test_*.py` files; 38 `.py` files under `tests/` (33 + 2 conftest + 3 `__init__`). §18.1 says 36.
Correct it when you transcribe the baseline.

---

### V-82 · P1 · The anti-fabrication guard does not scan the layer where the fabrication is

`tests/unit/test_no_fabrication.py:57-63`:

```python
def test_guard_1_no_dummy_or_mock_in_real_adapters() -> None:
    checked_subdirs = ["llm", "images", "sources", "search", "publish", "renderer", "audio"]
    for subdir in checked_subdirs:
        adapter_path = ADAPTERS_DIR / subdir
```

Guard 1 — the guard for "no hardcoded payload in a real component" — scans **seven subdirectories of
`adapters/` and nothing else**. `application/` is never scanned for it.

Both invented payloads this session found are in `application/agents/`:
`ResearchAgent`'s fabricated `SearchResultItem` (**V-81**) and `ScriptAgent`'s
`"Archival primary source records."` placebo (**V-67**). Guard 7 *does* walk `SRC_DIR`
(line 253), but only for plausible-history patterns — centuries, dated claims, named polities,
attestation language — and neither string matches any of them.

The guard was built to the shape of the 2026-08-29 incident, which happened in an adapter. The next
one happened one layer up, and the detector cannot see it. That is the same lesson as
`AUDIT-2026-08-29.md` §18's closing line, applied to the guards themselves.

**T-123 — extend Guard 1 to `application/`.**
*Done when:* Guard 1 scans `application/agents/` and `application/usecases/` for canned payloads and
literal fallbacks, and it **fails** on the current tree until V-67 and V-81 are fixed — a guard that
passes on the day it is written has not been shown to fire (the precedent is
`test_guard_7_detector_catches_a_fabricated_sentence`).

---

### V-83 · P2 · The disaster-recovery commands have no test

`atlas backup` and `atlas restore` (`apps/cli/main.py:443-491`) are the tools **R11** points at
("Back up first, record what was removed and why"). No test imports them, drives them, or asserts
that a dump plus blobs round-trips. The only coverage the CLI has is
`tests/unit/test_cli_commands.py`, which covers the run/gate/catalog surface.

Related and separate: the "not imported by any test" sweep also lists the seven network adapters and
the orphans, which are already registered as **T-58** and **T-28** — no new finding there. The
routes, `schemas.py`, `logging.py` and `redaction.py` appear in that sweep too but are exercised
indirectly through the HTTP client and the redaction tests, so their appearance is an artefact of the
method, not a gap.

**T-124 — one round-trip test for backup/restore against the test database.**

---

### What is provably true about Atlas without trusting a single test

§18.6's closing question, answered from what this session actually executed or read out of a
database:

**Provable.**
- The schema applies and rolls back cleanly through 7 migrations to 30 tables, on two databases.
- The HTTP surface is exactly the 15 paths / 20 operations `ARCHITECTURE.md` §2.1 describes, and the
  two unauthenticated routes are the two it names.
- An operator can create a Domain, a Topic and a Channel over HTTP with no terminal, and a duplicate
  is refused with a 409 and an unknown Domain with a 404 — *observed in the probe, not read from a
  test.*
- The production `Container` resolves eleven ports and none of them is a fake.
- `StubRenderer` produces a real MP4 at the requested resolution with WebVTT cues computed from the
  persisted Timing Plan, through real ffmpeg.
- The dashboard builds, and its components render API responses rather than fixtures.
- Provider API keys never enter a URL, a log or an error message.

**Not provable, and claimed anyway somewhere in the documents.**
- That a failed Run leaves any record at all (**V-20** — it does not).
- That a rejected gate leads anywhere (**V-21** — it does not).
- That the migrated schema matches the models (**V-49** — it does not).
- That any real provider call works, at all (**V-40** — the model ID is retired; no call has ever
  been made).
- That the Focus, the Research Profile, the publishing schedule or the impact index affect anything
  (**V-41, V-42, V-47, V-48, V-77** — none of them has a production reader or writer).
- That the queue exists in any form (**V-18, V-19, V-45, V-51**).
- That the dashboard can be deployed (**V-52**).
- **That a claim marked `verified` was verified** (**V-58** — a model saying "unverified" promotes it).
- **That a quality report's scores were produced by the judge** (**V-59** — seven of eight can be
  Atlas's own 80.0) **or that its deterministic checks were run** (**V-60** — two are `True`).
- **That a source is what its `source_tier` says** (**V-80** — every source is written `primary`), or
  that it was found rather than guessed (**V-81**).
- **That an artifact can be rebuilt** (**V-78** — `code_version` is a constant and `prompt_version` is
  a name).
- **That the knowledge base contains only what its sources say** (**V-71** — nothing stops a page
  from writing its own claims).
- That a Run's soundtrack exists after stage 14 (**V-62**).

---

## 7. The ordered list

New tasks first where they block, merged with `AUDIT-2026-08-29.md` §15.9's open list. Re-derive this
order only if you disagree with a reason, not because a different item looks easier.

| # | Task | Size | Why here |
|---|---|---|---|
| 0 | **T-103** — the verification verdict must be an enum, not a substring (V-58) | tiny | **The smallest fix on this list and the worst defect on it.** A model answering "unverified" marks the claim VERIFIED, and a missing field defaults to VERIFIED. It is the only path to that status and rendering gates on it. Two lines and a parametrized test. Nothing else on this list matters if the verified flag does not mean verified. |
| 1 | **T-69** — a failed Run must survive (V-20) | medium | P0 data loss on all three entry points, probed on two. It destroys the audit trail R11 exists to protect and the quota rows Invariant 8 depends on. Every debugging session after this one is blind until it is fixed. |
| 2 | **T-113** — source text is data, not instructions (V-71, V-72) | medium | P0. A hostile page writes its own claims, the verbatim guard passes them, and T-103's fix is what stops them reaching VERIFIED. Do it with T-103, not after. |
| 3 | **T-95** — close the schema drift, add `alembic check` to CI (V-49, corrected) | small + migration | P0 and cheap: three missing foreign keys, a JSON/JSONB drift, and nine redundant model flags to delete. Invisible because the migration test asserts nothing. Do it before anything writes more rows. |
| 4 | **T-78 + T-79** — fail closed, and set the deployment posture (V-29, V-30) | small | P0 security. The bypass is one boolean expression; the posture is one Compose change. **T-57 closes inside T-79** — the dashboard already sends the key. |
| 5 | **T-104 + T-105 + T-108** — the quality gate must measure (V-59, V-60, V-65) | small | The last gate before publish currently invents up to seven of eight scores, hardcodes two of six deterministic checks to `True`, and carries an unused override hook. Cheap, and it is what makes T-36's golden set meaningful later. |
| 6 | **T-122 + T-121** — no invented source, no asserted tier (V-81, V-80) | small | R1/R2 broken in `application/`. Fix these before **T-123**, which is written to fail until they are. |
| 7 | **T-123** — extend Guard 1 to `application/` (V-82) | small | The detector cannot see the layer the last two fabrications were in. Land it red, then green. |
| 8 | **T-114** — the fetcher must not be an SSRF primitive (V-70) | small | It is what makes T-113 reachable from outside a search result. |
| 9 | **T-106** — `render_prompt` must not interpret backslashes (V-61) | tiny | A source containing `\1` crashes extraction today, probed. One line. |
| 10 | **T-67** — build the queue ADR-0001 decided, or supersede it | medium + ADR | Unchanged from §15.9. Now also carries **V-45** (no reaper/retry/backoff/dead-letter, `step_name` dropped on enqueue, 60 s GPU TTL) and **V-51** (the `dramatiq` path still reproduces V-18). T-69's transaction boundary is the same seam — sequence them together. |
| 11 | **T-68** — the API must stop running the pipeline in the request | small | Depends on T-67. |
| 12 | **T-29 (re-scoped) + T-30 (re-scoped) + T-88** — implement ADR-0012 (V-40) | medium ×2 | The declared Gemini limit is 75× the measured one and the shipped model ID returns 404. **T-34 cannot succeed until this lands**, and every hour spent elsewhere on the assumption that a real run is close is wasted. |
| 13 | **T-119** — record the code version and the prompt hash (V-78) | small | Same provenance surface as T-29, and Invariant 7 is unanswerable until both stop being constants. Do it in that change. |
| 14 | **T-61** — fit the Timing Plan, or amend ADR-0006 | medium + ADR | Now also carries **V-63** (the schema permits 0.5 s to unbounded, far wider than the 36–81 s prompt band) and **V-64** (the judge's word budget is 100–160 where SPEC says 110–150). |
| 15 | **T-92** — meter the attempt, not the success (V-44) | small | With T-29/T-30. On a 20-a-day budget an unrecorded failed call is the difference between "I have 4 left" and "I have 1". |
| 16 | **T-120** — meter the sound library; widen Guard 9 to every provider port (V-79) | small | ~31 unmetered Freesound calls per Run, invisible because Guard 9 only knows about `llm` and `embedder`. |
| 17 | **T-70** — make a rejection do something, and fix the copy that promises it (V-21, V-39, V-76) | medium | The only human-facing control that silently does nothing, and the modal tells the operator otherwise. |
| 18 | **T-117** — the approve shortcut needs a deliberate act (V-75) | tiny | One keystroke, no confirmation, on the action Invariant 9 protects. Rejection is guarded and approval is not. |
| 19 | **T-84** — no failure may render as a fact (V-35, V-36) | small | R13 at the surface R13 was written for. Two components, one Playwright assertion. |
| 20 | **T-71** — one convention for "row does not exist" (V-22) | small | Includes the `IntegrityError` → 500 on a concurrent `save_claim`. |
| 21 | **T-80** — constrain identifiers at the boundary; stop logging `str(exc)` (V-31) | small | |
| 22 | **T-115** — the backup tool must not print the database password (V-73) | small | R12 broken by the tool R11 depends on, plus a world-readable dump left in `/tmp`. |
| 23 | **T-81** — the actor comes from the credential (V-32) | small | After T-78, which creates the principal. |
| 24 | **T-85** — persist the fallback Focus; give the Active Focus a setter (V-37) | small | V-15's shape, still open. |
| 25 | **T-118** — reconcile ADR-0002 point by point (V-77) | medium | Four of seven decisions unbuilt, one inverted: Active Focus history is deleted where the ADR says append-only. Overlaps T-85, T-89, T-90 — do them as one pass over the Focus model. |
| 26 | **T-96** — a committing test fixture (V-50) | small | Prerequisite for trusting T-69's and T-67's tests. |
| 27 | **T-107** — persist the SoundTrack or delete stage 14 (V-62) | small | The one production artifact with no table; ADR-0016 lists four and there are five. |
| 28 | **T-53** — the unreachable gate-stage branch | tiny | Confirmed unreachable: all six stages it names always suspend (`gate_policy.py:47-63`). |
| 29 | **T-65** — how the CLI reports a domain error | tiny | Unchanged. |
| 30 | **T-87** — the empty-database walkthrough (T-64's own *Done when*) | small | After T-79, so the posture it exercises is the real one. |
| 31 | **T-99** — pin the API ↔ dashboard wire contract (V-53) | medium | The only remaining structural defence against V-03's root cause. |
| 32 | **T-60** — quota exhaustion suspends rather than fails | medium | Unchanged; do with T-29. |
| 33 | **T-58** — cassettes for the seven network adapters | medium | Unchanged. Before T-34. |
| 34 | **T-89** — enforce the Research Profile, or record it inert (V-41) | medium | Before T-34: it decides which sources a real run may use — and today every source is written `primary` regardless (T-121). |
| 35 | **T-90** — the Focus must affect something, or be recorded inert (V-42) | medium | Same reason; part of T-118. |
| 36 | **T-34** — one honest real-provider run | a session | Blocker list grew: T-103, T-69, T-29, T-30, T-88, T-58, T-61, T-113. Without T-103 the run's verified claims mean nothing; without T-69 a failure erases the evidence you paid for. |
| 37 | **T-74** — persist asset candidates; the AI flag is a field (V-25) | medium | Supersedes and absorbs **T-54**. |
| 38 | **T-21** — `PUBLISH` refuses a stub publisher; ADR-0007 has no reader (V-47) | small | |
| 39 | **T-59** — read models for the gate review panels | medium | Depends on T-74. |
| 40 | **T-94** — write the impact index, or correct STATUS §3 (V-48) | small | |
| 41 | **T-72** — stage outputs state what happened (V-23) | small | |
| 42 | **T-93** — assert route provider == wired adapter (V-46) | tiny | Inside T-30. |
| 43 | **T-91** — enforce `tpm` or delete it (V-43) | tiny | |
| 44 | **T-98** — serve the dashboard, or record it dev-only (V-52) | small | |
| 45 | **T-75** — unblock the event loop; log ffmpeg's stderr (V-26) | tiny | |
| 46 | **T-109** — record the 8 kB extraction window (V-66) | small | |
| 47 | **T-110** — check for verified claims before the paid angle call (V-67) | tiny | Saves a Tier 2 request per doomed Run; deletes a placeholder T-123 will flag. |
| 48 | **T-111** — `strict=True` on the storyboard zips (V-68) | tiny | A short embedding batch silently drops beats from the video. |
| 49 | **T-77** — one mapper per row type (V-28) | small | |
| 50 | **T-86** — Research Profile on create, or say it cannot be authored (V-38) | tiny | With T-89. |
| 51 | **T-82** — decide how the dashboard authenticates (V-33) | small | With T-79. |
| 52 | **T-83** — the Compose password comes from the environment (V-34) | tiny | With T-115. |
| 53 | **T-116** — delete `apps/cli/backup_restore.py` (V-74) | tiny | A dead second backup that omits the database and exits 0 on failure. |
| 54 | **T-124** — one backup/restore round-trip test (V-83) | small | The tools R11 points at have no test. |
| 55 | **T-73** — two docstrings vs two `order_by` clauses (V-24) | tiny | |
| 56 | **T-76** — name the idempotency key for what it is (V-27) | tiny | With T-67. |
| 57 | **T-100 · T-101 · T-102 · V-57** — the bookkeeping four | tiny | STATUS §2's caption claim, the uncleared test overrides, the two unrecorded Topics, the test-module count. |
| 58 | **T-56** — does the dashboard need server push | tiny | Unchanged. |
| 59 | **T-25** — bind gates to artifact versions | migration + ADR | Unchanged. |
| 60 | **T-28** — wire or delete the five orphans | medium | T-30 wires `OllamaLlm`; **V-47** covers `PublishScheduler`. |
| 61 | **T-36 (+T-112)** — the golden quality set, counting rejected quotes (V-69) | a session | Blocks ADR-0012's measurement half. Fabricated-quote rejections are currently recorded only in a log line. |
| 62 | SPEC Phase 6 — knowledge system | a phase | Unchanged. |
| 63 | SPEC Phase 7 — the real renderer | a phase | Unchanged. |

---

## 8. Reproducing every piece of evidence

```bash
uv sync --all-extras

# Baseline (§0)
uv run ruff check . && uv run mypy . && uv run pytest
uv run pre-commit run --all-files
pnpm install && pnpm test && pnpm -r build
uv run python -c "from apps.api.main import app; p=app.openapi()['paths']; print(len(p), sum(len(v) for v in p.values()))"
find tests -name 'test_*.py' | wc -l        # V-57: 33, not 36

# V-49 — schema drift. Safe: touches atlas_test only, and restores it to base.
ATLAS_DATABASE_SYNC_URL=postgresql+psycopg://postgres@localhost:5432/atlas_test uv run alembic upgrade head
ATLAS_DATABASE_SYNC_URL=postgresql+psycopg://postgres@localhost:5432/atlas_test uv run alembic check
psql "postgresql://postgres@localhost:5432/atlas_test" -c \
  "select conrelid::regclass, conname, contype from pg_constraint
   where conrelid::regclass::text in ('gates','approvals','model_calls') and contype='f';"
ATLAS_DATABASE_SYNC_URL=postgresql+psycopg://postgres@localhost:5432/atlas_test uv run alembic downgrade base

# V-20, V-22, V-30, V-31 — one probe. It creates rows in atlas_test ONLY.
#   Write a script that: sets ATLAS_DATABASE_URL to atlas_test, imports apps.api.main:app,
#   overrides get_pipeline_runner with an object whose run_pipeline raises StepExecutionError,
#   and drives httpx.AsyncClient(ASGITransport(app, raise_app_exceptions=False)).
#   Then count rows in runs/steps/gates in a fresh session. Do NOT override get_db_session —
#   the real session is the thing under test. Downgrade atlas_test to base afterwards.

# V-37, V-41, V-42, V-47, V-48 — repository methods with no production caller
grep -rn "set_active_focus\|record_claim_usage\|save_window\|save_blackout_rule\|save_entity" \
  --include=*.py packages apps tests | grep -v "def \|ports/"
grep -rn "research_profile\|source_tier_floor\|source_allowlist" --include=*.py packages apps | grep -v test
grep -rn "captured_focus" --include=*.py packages/atlas/src/atlas/application

# V-40 — ADR-0012 against the code
grep -n "rpd_limit\|gemini-2.0-flash" packages/atlas/src/atlas/adapters/llm/gemini.py
grep -n "rpd\|provider=" packages/atlas/src/atlas/platform/quota.py packages/atlas/src/atlas/application/policies/quota_policy.py

# V-45, V-51 — the queue's missing half
grep -rn "reaper\|stuck\|dead.letter\|backoff\|retry" --include=*.py packages apps | grep -v test
grep -rn "set_broker" --include=*.py packages apps tests
grep -n "redis" pyproject.toml   # no match

# Live application database, read-only
psql "postgresql://postgres@localhost:5432/atlas" -c \
  "select (select count(*) from runs) runs, (select count(*) from focus) focus,
          (select count(*) from active_focus) active, (select count(*) from topics) topics;"

# ── second pass ──────────────────────────────────────────────────────────────

# V-49 correction — the database is better indexed than the models declare
psql "postgresql://postgres@localhost:5432/atlas_test" -Atc \
  "select indexdef from pg_indexes where schemaname='public'
   and indexname in ('ix_quota_window','ix_steps_idempotency','ix_pub_windows_lookup');"

# V-61 — a source containing a backslash-digit sequence crashes extraction
uv run python -c "
from atlas.prompts.loader import render_prompt
render_prompt('claim_extraction_v1', topic_title='T', source_title='S', source_url='u',
              source_tier='primary', source_text=r'see backref \\1 here')"
#   -> re.PatternError: invalid group reference 1 at position 13

# V-20 (CLI half) — probed. Seed a Domain/Topic/Channel in one _managed_cli_context,
#   then in a second context create a Run and raise inside the `async with`.
#   Observed: "run.created run_id=run_edfc…" logged, then `rows in runs: 0`.

# V-58 — read it, then write the failing test
sed -n '60,70p'   packages/atlas/src/atlas/application/agents/models.py       # status: str = "verified"
sed -n '105,120p' packages/atlas/src/atlas/application/agents/verification.py # "verif" in raw_status

# V-59, V-60, V-65 — the judge
sed -n '96,150p' packages/atlas/src/atlas/application/agents/judge.py

# V-62 — the SoundTrack has nowhere to go
grep -n "async def" packages/atlas/src/atlas/adapters/persistence/repositories/production_repository.py
grep -rn "SoundTrack" --include=*.py packages apps | grep -v test

# V-78 — provenance constants
grep -rn 'code_version=' --include=*.py packages apps | grep -v test
grep -rn "get_prompt_hash" --include=*.py packages apps | grep -v test   # no production caller

# V-80, V-81 — the research agent
sed -n '45,80p' packages/atlas/src/atlas/application/agents/research.py

# V-82 — what Guard 1 actually scans
sed -n '57,63p' tests/unit/test_no_fabrication.py

# V-75 — the approve keybinding
sed -n '54,68p' apps/web/src/components/ApprovalQueue.tsx
```

**Both databases were left exactly as they were found:** `atlas` untouched at `b1c4d7e90a25` with its
4/3/3 catalog rows and 0 runs; `atlas_test` downgraded to base, which is where `pytest` leaves it.

---

## 9. What this session did not check

Stated so you do not read absence as clearance.

- **No provider call of any kind.** No Gemini, Ollama, Freesound, Wikipedia, Wikimedia, Internet
  Archive or plain HTTP request was made. The seven network-backed adapters remain verified only by
  hand (**T-58**).
- **No browser walkthrough against a live API.** Angle 3 was done by reading every component and by
  running the mocked Playwright suite. The empty-database walkthrough is **T-87** and is still owed.
- **`docker compose up` was not run.** V-51 and V-52 are read from the Compose file, the Caddyfile,
  the Vite config and the absence of a `set_broker` call. Confirm them by running it — that is the
  cheapest possible test of both.
- **`apps/renderer` and `packages/tokens` were not reviewed** beyond confirming they build. The
  renderer is Phase 7 and deferred (D57).
- **Seven ADRs still not read line by line.** ADR-0001, 0002, 0004, 0006, 0007, 0012 and 0016 were
  (0002 and 0016 on the second pass, producing V-77 and V-62). ADR-0003, 0005, 0008, 0009, 0011,
  0013, 0014, 0015, 0017 and 0018 were consulted only where a finding touched them. §18.5's
  *Done when* — "every ADR read against its implementation" — is **still not met**; the two read on
  the second pass yielded five divergences between them, so the remaining ten are worth the hour.
- **`domain/` is partially audited.** `agents/models.py`, `quality/models.py` (the `evaluate`
  factory) and `script/models.py`'s timing types were read. `knowledge/invariants.py`,
  `knowledge/upcast.py`, `media/models.py` and `assets/models.py` were not.
- **`KnowledgeRepository` was not read**, so `save_version`'s traceability validation — the check
  `STATUS.md` credits for Invariant 1 — is confirmed only by its call site, not by its body. Read it
  before trusting that row of the invariant table.
- **`apps/renderer` and `packages/tokens` were not reviewed** beyond confirming they build.
- **The `atlas` application database was read, never written.** The three Topics, four Domains and
  three Channels in it are as this session found them.
- **No fix was attempted, and no test was written.** Every task above is unstarted.

---

## 10. Bookkeeping when you act

From `STATUS.md` §5's close-out checklist, the items this work will trip:

- Transcribe §2–§6 into `AUDIT-2026-08-29.md` **§19** with the IDs as given (V-20 … V-57), then merge
  §7 into **§15.9**. Do this **before** the first fix.
- Every number in `STATUS.md` §0 must be re-measured in the session that writes it (**R7**). §0 above
  is dated 2026-09-05 and is not yours to carry forward.
- `STATUS.md` §2 has four claims this file contradicts — the e2e caption claim (V-54), "live API"
  browser tests (V-53), the invariant table's Invariant 9 row (V-25), and "impact index beyond
  `claim_usages`" (V-48). Move them to §3 or §4 with the finding ID.
- `SPEC.md` §17 needs rows for: ADR-0012 unimplemented (V-40), the source policy unenforced (V-41),
  the Focus inert (V-42), ADR-0007 unbuilt (V-47), rejection without rework (V-21).
- `ARCHITECTURE.md` §11 needs rows for: the schema drift (V-49), the dashboard with no deployment
  (V-52), the worker that cannot start (V-51). §2.1 is **correct as it stands** — do not touch it
  unless you add a route (T-85's activate route is one).
- `DECISIONS.md` gets a D-number for every judgement call, and an ADR is required for: any change to
  the transaction boundary (V-20 changes durability semantics ADR-0001 describes), superseding
  ADR-0001 or ADR-0006, and applying ADR-0012 (which is a change of provider category wiring).
- **R9 still binds.** None of these fixes may be written as an ADR that permits an invariant to be
  weakened. If a fix seems to need that, the fix is wrong.
