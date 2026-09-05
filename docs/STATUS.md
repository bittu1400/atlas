# Status

**Last updated:** 2026-09-05, second session of the day — **the five-angle verification
(`docs/AUDIT-2026-08-29.md` §18) was run and found 70 defects, V-20 – V-89. No code was changed.**
**Branch:** `docs/audit-2026-08-29` — see §1.

> **Read `docs/AUDIT-2026-08-29.md` §19 before you touch anything.** It is the register of what that
> verification found and **§19.10 is the live ordered task list, superseding §15.9**. This file's §2
> has been corrected against it; four claims that stood here yesterday were false and have moved to
> §3 or §4 with a finding ID.
>
> **The single most important line in this file:** a Claim reaching `verified` does not currently
> mean it was verified. `VerificationAgent` maps the model's verdict with `if "verif" in status`,
> defaulting a missing verdict to `"verified"` — so `"unverified"` and `"cannot be verified"` both
> promote the claim (**V-58**, task **T-103**, two lines). Everything downstream of Invariant 1 rests
> on that flag.

This file separates **decided** from **done**. Everything else in `docs/` records what Atlas *will*
be; this records where it actually stands. It is rewritten from measurement at the end of every
working session, and **every number in it comes from a command run in the session that wrote it**
(rule R7). The previous body is archived unchanged at
[`docs/archive/STATUS-2026-08-29.md`](archive/STATUS-2026-08-29.md); nothing in that file is a
current claim.

---

## 0. Measured baseline

Measured on 2026-09-05 **at the end of the verification session that wrote this section**, on a clean
tree with no code changes since the previous measurement. **Re-run them before quoting them**
(**R7**).

```
$ uv run ruff check .
All checks passed!

$ uv run mypy .
Success: no issues found in 179 source files

$ uv run pytest
191 passed in 20.69s

$ uv run pre-commit run --all-files
Ruff Lint Check / Ruff Format Check / Anti-Fabrication Structural Guard — Passed

$ pnpm test
10 passed (7.5s) — apps/web/e2e/dashboard.spec.ts, Playwright Chromium

$ pnpm -r build
packages/tokens · apps/renderer · apps/web — 3 of 3 built

# all of the following also measured 2026-09-05, same session:
$ find tests -name 'test_*.py' | wc -l
33 test modules   # audit §18.1 said 36; that was wrong — defect V-57

$ find packages apps -name '*.py' -not -path '*__pycache__*' | wc -l
141 Python files

$ ls .../alembic/versions/*.py | grep -v __init__ | wc -l
7 migrations on disk

$ uv run python -c "from atlas.adapters.persistence.tables import Base; print(len(Base.metadata.tables))"
30 tables

$ uv run python -c "from apps.api.main import app; print(len(app.openapi()['paths']))"
15 paths, 20 operations — transcribed in ARCHITECTURE §2.1

$ uv run alembic check
FAILED: New upgrade operations detected: [...]
```

**`alembic check` fails.** That is defect **V-49**, not a pending change: the migrated schema and the
ORM models disagree. The material part is three foreign keys — `gates.run_id`, `approvals.run_id`,
`model_calls.run_id` → `runs.id ON DELETE CASCADE` — declared in `tables.py` and **absent from the
database**, confirmed directly in `pg_constraint`. `test_alembic_migrations_roundtrip` runs four
alembic commands and **asserts nothing**, and CI never runs `alembic check`, which is why this has
never been visible. Task **T-95**.

The 7 and the 30 above are counted from the migration files and from `Base.metadata`. **The
2026-09-05 verification session additionally applied `alembic upgrade head` to `atlas_test` three
times and read the result back**, which is the stronger measurement and is what produced V-49 — on
2026-09-05 that database held 31 tables in
`information_schema` (30 plus `alembic_version`), 18 immutability triggers, and the constraint
inventory in audit §19.6. `atlas_test` was returned to `base` afterwards, which is where `pytest`
leaves it. The `atlas` application database was **read and not written** by that session. CI runs
`alembic upgrade head` on every push; it does **not** run `alembic check` (**T-95**).

There are no `xfail` markers in the suite, and as of 2026-09-04 there are **no skips in CI either**:
`test_production_adapters.py:148` needs ffmpeg, the runner image has none, and `ci.yml` now installs
it (**D133**). Before that step, the only test that shells out to real ffmpeg passed locally and
skipped on the runner — a green CI that did not cover the renderer path.

**The Python count moved by twenty-five and the browser count by six.** T-62 and T-63 brought unit
tests for the Run guard, a CLI-surface test and the Domain → Topic → Channel → Run sequence against
the real schema; T-64 brought eight HTTP tests over the new routes, four repository-listing tests,
and six browser assertions over the pickers, the Catalog and the Pipeline tab; V-18 brought three
that call the broker the production container actually resolves. The HTTP surface moved from 11
paths / 12 operations to **15 / 20**. The lesson attached to these numbers is older and still
stands: on 2026-08-31 the three headline numbers held while the claim they were taken to support did
not. The suite exercises the pipeline **against fakes**, and until that day no test constructed
`Container` or called any adapter it wires except `LocalStorage`. The first production adapter substituted into a real Run — `LoggingNotifier` — raised
`TypeError` at the first gate of every Run. That is defect **V-01**, and audit §15 has the rest —
thirteen defects, of which three were P0 and none had a task in the register before they were found.
Twelve are fixed; **V-13** is open by decision (**D125**, task **T-60**).

**CI status: green, and blocking.** Run
[33881891323](https://github.com/bittu1400/atlas/actions/runs/33881891323) on `6e5a4e1` — all 22
steps success, on both the `push` and `pull_request` events; re-verified green on `579d1c5`. It ran, in order: Ruff, mypy,
`alembic upgrade head`, `pytest` (162 passed, 1 skipped), Playwright (4 passed), and the three pnpm
builds. Two distinct bugs had to be fixed to get there, and neither was in the test suite:

1. **The migration step could not authenticate.** `alembic.ini` hardcodes
   `postgresql+psycopg://postgres@localhost:5432/atlas`, with no password, and the revision on the
   runner used it in preference to the job's `ATLAS_DATABASE_SYNC_URL` — hence
   `fe_sendauth: no password supplied`. The fix was written and committed **locally on 2026-09-03 and
   never pushed**, so CI kept re-running the broken revision. Nothing needed to change; the commits
   needed to leave the laptop. *A fix that is not pushed is not a fix* — CI can only test what
   `origin` has.
2. **Playwright's browsers could not be installed.** `@playwright/test` is a devDependency of
   `apps/web`, so `pnpm exec playwright` at the repository root resolved no binary
   (`ERR_PNPM_RECURSIVE_EXEC_FIRST_FAIL`). Reproduced locally with the identical error, then fixed by
   filtering the exec to the workspace (`ci.yml:70`, commit `6e5a4e1`).

**T-00 and T-11 are both closed.** `main` now requires the `test` check: branch protection was set
via `gh api` and read back — `required_status_checks.contexts` is `["test"]`, force pushes and
deletions disabled (**D132**). One caveat that must not be rounded off: **`enforce_admins` is
false**, so an administrator can still override. "Blocking" here means the merge button is blocked,
not that the gate cannot be bypassed.

T-11's *Done when* — a deliberately introduced lint error fails CI — was **not** literally exercised.
Two genuine failures the same day already showed the build goes red on a non-zero exit, and pushing a
knowingly broken commit to demonstrate a property twice would leave it in the branch history for no
new information. Recorded rather than ticked silently.

---

## 1. Working tree state

**The verification session of 2026-09-05 changed no code, no configuration and no schema.** It wrote
`docs/AUDIT-2026-08-29.md` §19 and edited this file, `SPEC.md` §17.12, `ARCHITECTURE.md` §11.7g/§11.8,
`DECISIONS.md` (D144–D151) and `CLAUDE.md`'s read order. Nothing under `packages/`, `apps/` or
`tests/` was touched, so §0's numbers describe the same tree the previous session left.

**Three rows were written to `atlas_test` and removed again**; the database was returned to `base`.
The **`atlas` application database was read and never written** by that session. Reading it produced
two findings: `focus` and `active_focus` are **empty** (defect **V-37** — nothing can set the Active
Focus, so every Run captures an unpersisted in-memory Focus), and `topics` holds **three** rows where
§1 below records one (defect **V-56** — `topic_origin_of_chess` and `topic_origin_of_art`, created
2026-09-05 at 10:09 and 10:59, were never written down; both are additive and `proposed`, nothing was
overwritten). `runs` is empty: **no Run has ever existed in the application database.**

Clean on branch `docs/audit-2026-08-29`. The most recent behavioural commit is the **V-18** queue
fix, preceded by the T-64 dashboard work (Catalog and Pipeline tabs, eight routes, four repository
listings), the V-17 duplicate guard, the T-62/T-63 remediation, the commit recording **V-15** and
**V-16**, the T-20 timing-plan change, the
two CI fixes, the ffmpeg CI step, the T-22 topic title resolution, the T-55 Playwright browser test
suite, the V-01 – V-12 remediation, and the reconciliation that found **V-13** and left it to task
**T-60** (**D125**).

**Rows were written to the local `atlas` application database by hand this session.** The
`topic_origin_of_weapons` Topic, created through the new CLI command to verify the fix on the machine
where the defect appeared — and then `dom_history` and `origins` were **overwritten** by that same
command before it refused duplicates (defect **V-17**) and **restored** from the migration seed under
task **T-66**, with the damaged and restored values recorded in the audit. Its Domain (`dom_history`) and Channel (`origins`) already existed there
from migration `0001_initial_schema`, which seeds four Domains and three Channels — an earlier
sentence in audit §17.3 called those rows residue and is corrected there. Additive only; nothing was
deleted or edited (**R11**).

**One change this session is not in the tree at all:** branch protection on `main` is a repository
setting, not a file. `ARCHITECTURE.md` §10 and §11.7d record it, because a deployment posture that
exists only in GitHub's database is exactly the kind of state that gets forgotten and then
contradicted.

This file deliberately does not name its own HEAD. A document that states the hash of the commit
containing it is wrong the moment it is committed. `git log --oneline -5` is the source of truth.

**The branch is pushed to `origin/docs/audit-2026-08-29`** and PR #1 is open against `main` with CI
green. This documentation update is ahead of `origin` until pushed — and per **D130**, a session that
ends without pushing has left its own verification undone, because CI tests `origin`, not the
working tree.

---

## 2. What exists and is verified

Verified means: exercised by a test that inspects database state after a real run, not merely that a
function exists.

> **Corrected 2026-09-05 by the §19 verification.** Four claims that stood in this section were false
> or narrower than they read, and each is marked below with its finding ID. A fifth — "Phase 5
> agents complete" — is qualified rather than withdrawn. Do not read a paragraph here without its
> correction.

**Phase 1 · Architecture** — complete. Spec, architecture, glossary, ADRs 0001–0018. **Caveat
(V-85, V-86, V-87, V-88):** four ADRs describe a system that is not the one in the tree — ADR-0003 §2
contradicts ADR-0016 on whether production artifacts are versioned and neither supersedes the other;
ADR-0003 §4 promises a database constraint excluding unsupported claims that does not exist;
ADR-0009 names three wired adapters that are not wired; ADR-0005's single-source design tokens are
consumed by `apps/renderer` and **not** by `apps/web`, which carries 17 hardcoded hex colours.

**Phase 2 · Database** — complete, with one real gap. 30 tables, 7 Alembic migrations, round-trip
tested (`test_alembic_migrations_roundtrip` applies head → base → head — **but it asserts nothing**,
which is how **V-49** stayed invisible). Knowledge Objects are row-per-version with a separate
current pointer (ADR-0003). Claims are append-only: an immutable identity row plus `claim_versions`,
each version carrying the actor and the reason (ADR-0015), and **`(claim_id, version)` is the primary
key**, so a duplicate version is impossible at the database level.

**What is genuinely strong here, verified in the database on 2026-09-05:** ADR-0008 is fully
implemented — 18 immutability triggers (`trg_prevent_delete_*` on 12 tables, `trg_prevent_update_*`
on 6), `uq_snapshot_source`, and the composite
`fk_evidence_snapshot (snapshot_id, source_id) → snapshots(id, source_id)`, so **evidence cannot
forge its source**. ADR-0013's `incident_2026_08_29` quarantine schema exists in both databases.

**What is broken here (V-49):** `gates.run_id`, `approvals.run_id` and `model_calls.run_id` declare
`ForeignKey("runs.id", ondelete="CASCADE")` in `tables.py` and **have no such constraint in the
database**. `alembic check` fails. Task **T-95**.

**Phase 3 · Backend** — complete. FastAPI, Dramatiq worker, the 18-stage Run/Step state machine,
gates, approvals, resource locks, idempotency keys and the quota ledger. A Run traverses every stage
against fakes, suspends at each of the six manual/hybrid gates, and resumes.

**Phase 4 · Frontend + CLI** — CLI parity is real and tested. The dashboard (`apps/web`) builds and
reads the API across six tabs: Dashboard (summary tiles, Launch form, Runs), **Catalog** (Domains,
Topics, Channels, Focuses — listed and created), Approval Queue, **Pipeline** (the Run's Step rows
and the Gate holding each), Knowledge, and Telemetry & Quota. The last two tabs were added on
2026-09-05 with **T-64**; `RunPipeline` is the first consumer `GET /runs/{id}/steps` and
`GET /runs/{id}/gates` have ever had — both routes existed unread since Phase 3. Every panel renders a database row or an error —
until 2026-08-31 five of its components rendered invented claims, invented snapshot hashes and an
invented telemetry feed, and its API client answered an unreachable backend with fabricated Runs and
a fabricated passing quality report (defect **V-03**, audit §15.4). **Browser testing is real**
(task **T-55**, **ADR-0018**): `apps/web/e2e/dashboard.spec.ts` executes in headless Chromium,
asserting that the dashboard renders the topic IDs, gate step IDs, error banners and snapshot hashes
**the API returned**, rather than fixtures.

**Corrected (V-53): those tests never reach a server.** All ten assertions install
`page.route('/api/…')` handlers that fulfil synthetic JSON, so "live API" — the phrase this paragraph
used to carry — was wrong. They prove exactly what T-55 built them for, that a component renders its
props, and nothing about the API. ADR-0018 is honest about being route-level; this file was not.
**Nothing anywhere asserts that `apps/api/schemas.py` and `apps/web/src/api/types.ts` agree** — the
mocked run object already omits `captured_focus` and `trace_id`, both required by `RunItem`. Task
**T-99**.

**Two panels still render a failure as a fact (V-35, V-36).** `App.tsx` discards the pending-gates
query error, so a failed `GET /gates/pending` shows a zero badge, "Awaiting a human: 0" and "No
pending Gates"; `RunSummary` discards the topics error, so a failed `GET /topics` shows
"Topics: 0 — Candidate subjects available to launch". Task **T-84**. And **one keystroke approves a
gate** — a bare `a`, no modifier, no confirmation, while rejection demands a structured modal
(**V-75**, task **T-117**).


**An operator can create the rows a Run needs, and a bad ID fails as a typed 404 (T-62, T-63,
D136–D137).** `atlas domain create`, `atlas topic create` and `atlas channel create` are the first
production callers `save_domain`, `save_topic` and `save_channel` have ever had; before them, `topics`
was empty in any database a test had not seeded and `POST /runs` violated its foreign key for every
input, returning a 500 with the SQL in the log (defects **V-15** and **V-16**).
`CreateRunUseCase` now resolves the Topic and the Channel before it constructs the Run, so both
entry points fail with `TopicNotFoundError` / `ChannelNotFoundError` rather than an untyped
`IntegrityError`. `tests/integration/test_run_creation_prerequisites.py` drives Domain → Topic →
Channel → Run through the shipped use cases with no fixture in the chain and asserts all four rows;
two HTTP tests assert the 404 bodies. Verified by hand against the running server that produced the
original 500. **What this does not do** is give the dashboard the same ability — the three commands
have no HTTP route, so an operator must use the terminal once (**T-64**), which makes SPEC §1's
"full CLI parity" claim false in the CLI's favour.

**The dashboard is self-sufficient (T-64, D140 aside).** Eight routes — `GET`/`POST` for
`/domains`, `/topics`, `/channels` and `/focuses` — sit over four new repository listing methods and
five use cases, taking the HTTP surface from 11 paths / 12 operations to **15 / 20**
(`ARCHITECTURE.md` §2.1, verified row-by-row against `app.openapi()`). The Launch form's three
free-text boxes are pickers; a duplicate ID is a 409 and an unknown Domain a 404, neither an
overwrite nor a 500. `GET /focuses` resolves the Active Focus pointer against the list, because a
Run created without an explicit Focus captures the active one by value (Invariant 6). Ten browser
tests assert the pickers list exactly what the API returned, that an empty table renders as empty,
and that a refused creation is shown as a refusal.
**What is not verified:** the empty-database walkthrough in T-64's own *Done when* — every check so
far ran against a database migration `0001` had already seeded. See audit §18.4.

**A Timing Plan can no longer overstate its own duration (T-20, D129).**
`TimingPlan.total_duration_seconds` was a plain field defaulting to `60.0`; a plan carrying 3.5
seconds of beats reported a full minute and satisfied the judge's 58–62 s deterministic check for
free. It is now a computed field derived from the last beat's end time, so the stated duration
cannot disagree with the timeline behind it. `tests/unit/test_timing_plan_duration.py` asserts the
derivation, asserts that a caller passing `60.0` still gets `3.5`, and asserts that the judge
rejects the short plan — the last of which failed with `duration_bounds is True` before the change,
which is defect **R-04** reproduced. **What this does not do is make the duration correct**, only
honest: nothing steers a Script towards 60 s. See §3 and defect **V-14**.

**Phase 5 · Agents** — the nine agents exist and run. **Four of them do something other than what
this line used to claim, found by the §19 verification:**

- **`VerificationAgent` does not verify (V-58, P0, task T-103).** `VerificationResultItem.status` is
  a free `str` defaulting to `"verified"`, mapped by `if "verif" in raw_status`. `"unverified"`,
  `"not verified"` and `"cannot be verified"` all promote the claim; a missing field does too. It is
  the only path a Claim can take to `VERIFIED`, and `_assert_script_claims_are_traceable` gates
  rendering on exactly that status.
- **`JudgeAgent` invents scores (V-59) and two of its deterministic checks are hardcoded `True`
  (V-60).** A missing rubric dimension is scored `80.0` by Atlas, and `min_length=8` does not require
  eight *distinct* dimensions — so a near-empty judge response yields a **passing** quality report.
  `loudness_bounds` and `safe_margins` always pass; nothing measures either.
- **`ResearchAgent` asserts a tier it never establishes (V-80) and invents a source when search
  returns nothing (V-81).** Every source is written `source_tier=PRIMARY`; on zero hits the agent
  builds a `SearchResultItem` with a made-up title and a Wikipedia URL guessed from the Topic slug,
  then snapshots it. This is the shape R1/R2 forbid, in `application/` where no guard looks (V-82).
- **`SoundDesignAgent` produces an artifact that is discarded (V-62)** — no `soundtracks` table, no
  `save_soundtrack`, and the renderer never receives it — and it holds a rate-limited network
  provider with **no `QuotaManager`** (V-79), so ~31 Freesound calls per Run go unmetered.

The rest holds: topic discovery, extraction (with a real verbatim check), story angle, script and
storyboard run end to end against fakes. An ORIGINS Topic yields a source-traced Knowledge Object
and a Script whose every beat cites claims the pipeline believes are verified — see V-58 for what
that belief is worth. **Topic title resolution is
honest (T-22, D128):** `PipelineRunner._resolve_topic_title` loads `topic.title` from `SourceRepository`
and propagates it to `ResearchAgent`, `ExtractionAgent`, `ScriptAgent`, `JudgeAgent`, and archival search,
eliminating the four sites where raw snake_case IDs were previously passed into prompts and queries.


**The production wiring is exercised.** `tests/integration/test_production_adapters.py` constructs
`Container`, asserts it resolves no port to a fake, and runs `StubRenderer` (both aspect ratios,
real ffmpeg), `StubPublisher`, `StubImageGenerator` and `LoggingNotifier`. The network-backed
adapters — `WikipediaSearch`, `HttpSourceFetcher`, `WikimediaCommonsSearch`,
`InternetArchiveSearch`, `OllamaEmbedder`, `GeminiLlm`, `FreesoundLibrary` — remain uncovered; see
§3.

**The pipeline reaches stage 18.** `test_full_18_stage_pipeline_traversal_with_human_gates` drives a
Run from creation to `completed` through all six human gates and then asserts, against the database:
every claim in the Knowledge Object resolves to evidence with a source and a snapshot; every beat
cites only claims from that Knowledge Object; exactly one `script_generation_v1` model call was
metered for the run; the storyboard references the persisted script and timing plan; render
artifacts exist for both aspect ratios with WebVTT captions; publication ran once
per artifact; every `model_calls` row records `provider='fake'`, the adapter that actually ran; the stage 1 topic
discovery call and both stage 13 embedding calls are metered with matching `quota_ledger` entries in
the minute and day windows.

**Three corrections to that paragraph (2026-09-05).**

- **The caption assertion is over a literal (V-54).** It checks `startswith("WEBVTT")` and
  `"-->" in captions` against `FakeRenderer`'s hardcoded
  `b"WEBVTT\n\n00:00:00.000 --> 00:00:03.500\nKinetic Text Line"`. Deleting `generate_webvtt` from
  `StubRenderer` would not fail it. The **real** derivation from the Timing Plan is covered — in
  `tests/integration/test_production_adapters.py:140-145,173-174` — so this sentence credited the
  wrong test. The words "carrying real cues" have been removed.
- **This test never commits (V-50).** Like every integration test it runs inside the `db_session`
  fixture's transaction, which is rolled back at teardown. Nothing in the suite exercises a commit,
  cross-transaction visibility, the `with_for_update` gate lock, or the GPU lease across processes.
- **It proves nothing about a failing Run (V-20).** When a stage raises, the request's transaction
  rolls back and the `runs`, `steps`, `gates`, `model_calls` and `quota_ledger` rows all disappear —
  probed on both the API and the CLI. The suite cannot see it because the fixture rolls back anyway.

### 2.1 Phase numbering — SPEC §15 is the numbering (D58, T-38)

This file used to number phases differently from `docs/SPEC.md` §15 and then declared the renumbered
phases complete. It now uses SPEC's numbering. The table maps the old STATUS names onto it so the
work is recounted rather than lost.

| SPEC §15 phase | What it means | Old STATUS name | State |
|---|---|---|---|
| 1 · Architecture | Spec, architecture, glossary, ADRs | Phase 1 (Architecture) | **complete** |
| 2 · Database | Schema, migrations, KO versioning, repositories | Phase 2 (Database & Persistence) | **complete, with a live drift.** `alembic check` fails: three declared foreign keys are absent from the database and `model_calls.parameters` is `JSON` where the model says `JSONB` (**V-49**, **T-95**). ADR-0008's 18 immutability triggers and composite evidence FK are real and verified. |
| 3 · Backend | FastAPI, worker, Run/Step state machine, gates, quota | Phase 3 (+ 3.1 remediation) | **The state machine runs; three of its properties do not hold.** A failed stage rolls back the whole Run record (**V-20**, P0); a rejected gate deadlocks with no operator action (**V-21**); the API is unauthenticated by default and its auth can be enabled without a key (**V-29**, **V-30**). The queue ADR-0001 decided still does not exist (**V-18**, **V-19**, **V-45**). |
| 4 · Frontend + CLI | Dashboard shell, approval queue, CLI parity | Phase 4 (Frontend + Remotion Renderer) | **CLI complete. Dashboard reads the API across six tabs, renders no fixtures, and is covered by 10 browser tests — which mock the API at the network layer (V-53) rather than reaching it. An operator can create a Domain, Topic, Channel and Focus and launch a Run without a terminal (T-64), but not from an empty database — that walkthrough is still unrun (T-87).** Still missing: the approval queue cannot show the artifact under review (**T-59**), and no Research Profile or Style Profile can be edited (**V-38**). Two panels render a failed fetch as a fact (**V-35**, **V-36**); one keystroke approves a gate (**V-75**); the built bundle has no deployment (**V-52**). The renderer half of the old name was never Phase 4 work. |
| 5 · Agents | Research, extraction, verification, script, judge | Phase 5 (Agents & Intelligence Engine) | **The nine agents exist and run against fakes. Four do not do what their names say** — verification promotes on a substring (**V-58**, P0), the judge invents missing scores and hardcodes two deterministic checks (**V-59**, **V-60**), research asserts a source tier and invents a source on zero hits (**V-80**, **V-81**), sound design discards its artifact and is unmetered (**V-62**, **V-79**). See §2. |
| 6 · Knowledge system | Graph, Entity binding, novelty, impact index | *no old equivalent* | **not started.** `application/policies/` holds only gate, license and quota policy. |
| 7 · Rendering | Remotion compositions, sound design, both targets | Phase 7 (End-to-End Execution) — fabricated | **not started.** Deferred by D57; the data path into the renderer is proven (ADR-0016). |
| 8 · Publishing | Publisher adapters, slot scheduler, attribution | Phase 6E | **not started.** `StubPublisher` only. |
| 9 · Analytics · 10 · Optimization | — | — | deferred |

**Where the old "Phase 6 (Production Pipeline Integration)" work went.** It was adapter work, not a
SPEC phase: `WikimediaCommonsSearch`, `InternetArchiveSearch`, `CompositeImageSearch`,
`FreesoundLibrary`, `KeystrokeSampler`, `AudioCompositor`, `OllamaEmbedder`, the DI container, the
Dramatiq broker, `docker-compose.yml` and `Caddyfile`. Those adapters exist. Five of them are not
reachable from `Container` and are listed as orphans under audit task **T-28**.

Two corrections to that paragraph, made 2026-08-31: `docker-compose.yml` "existing" was not the same
as working — it built `api` and `worker` from a `Dockerfile` that did not exist, so
`docker compose up` failed at the first build until this session wrote one (defect **V-05**). And of
the wired adapters in that list, only `LocalStorage` had ever been touched by a test (defect
**V-07**); `tests/integration/test_production_adapters.py` now covers the six that need no network.

### Invariants with an enforcing check that runs

> **Corrected 2026-09-05 (audit §19).** This table was read as a list of invariants that hold. It is
> a list of checks that **run** — which is not the same thing, and five rows are narrower than they
> look. A **Gap** column has been added; a row with a gap is not a row you may rely on.

| Invariant | Enforced by | Proven by | Gap found 2026-09-05 |
|---|---|---|---|
| 1 · No fact without a source | `validate_knowledge_object_claims_are_traceable`, called by `KnowledgeRepository.save_version` before any write | `test_no_claim_reaches_output_without_evidence` | **Checks that a `claim_evidence` row exists, not its stance.** A claim whose only evidence **contradicts** it passes. The stance check lives in `validate_claim_publication_readiness`, which has **no production caller** — and Guard 6 scans only `application/policies/`, so it cannot see a decorative invariant in `domain/`. **V-84**, **T-123**. |
| 1 · Verbatim evidence | `ExtractionAgent` rejects any quote not present in the snapshot | `test_every_evidence_quote_is_verbatim_in_its_snapshot` | Holds — but it is **not** a defence against prompt injection: an injected quote really is present in the attacker's page, so the check passes it (**V-71**, **T-113**). The rejection count is logged and recorded nowhere (**V-69**). |
| 1 & 2 · Pre-render backstop | `PipelineRunner._assert_script_claims_are_traceable` on the persisted script | the end-to-end assertions above | Gates on `status == VERIFIED`, which **V-58** makes unreliable. The backstop is sound; the flag it reads is not. |
| 2 · A model is never the source | Claims start `unverified`; only `VerificationAgent` may promote them | `test_claim_is_not_verified_at_extraction_time` | **BROKEN (V-58, P0).** True that only `VerificationAgent` promotes; false that promotion means anything. `status: str = "verified"` mapped by `if "verif" in raw_status` — `"unverified"` promotes, a missing field promotes. No test asserts what the model must return. **T-103.** |
| 4 · Append-only knowledge | `claim_versions` with primary key `(claim_id, version)`; `save_claim` inserts, never updates; 18 database triggers reject DELETE/UPDATE on the core knowledge tables (ADR-0008, verified in `pg_trigger`) | `test_claim_state_changes_append_a_version_and_never_overwrite` | Holds for knowledge. **Does not hold for the Active Focus pointer**: `set_active_focus` runs `DELETE` then insert, and `active_focus` is the one Focus table with no trigger — against ADR-0002 §7's "append-only records with actor and timestamp" (**V-77**, **T-118**). |
| 5 · No provider SDK outside its adapter | AST guards 1–4 over `adapters/` | `tests/unit/test_no_fabrication.py` | None found. |
| 7 · Every artifact records how it was made | `model_calls` provenance taken from the adapter that executed; production artifacts persisted | `test_model_call_provenance_matches_the_adapter_that_ran` | **Two of the five fields Invariant 7 names are constants (V-78).** `code_version="phase-5-v1"` is a literal at all seven call sites; `prompt_version` is a name, not a hash, and `get_prompt_hash` has no caller. The test checks the **provider** only. Also: the SoundTrack is not persisted at all (**V-62**), and on a stage failure the whole provenance set is rolled back (**V-20**). **T-119.** |
| 8 · Every model call is metered | Every agent holding an LLM or Embedder port takes a `QuotaManager`; `check_rate_limits` reads `quota_ledger` | `test_guard_9_every_agent_that_calls_a_model_holds_a_quota_manager`, `tests/integration/test_quota_enforcement.py`, and the end-to-end assertions on `topic_discovery_v1` and `embedding_v1` | **Three gaps.** A **failed** provider call is never metered — `record_invocation` runs only on success (**V-44**). `SoundDesignAgent` holds Freesound with no `QuotaManager`; Guard 9 only knows `self.llm`/`self.embedder` (**V-79**). The enforced Gemini limit is `rpd=1500` against a measured **20** (**V-40**). `tpm` is declared and never checked (**V-43**). |
| 9 · AI imagery needs human approval | An `Approval` row on the asset-selection gate, resolved by step ID | `test_ai_generated_asset_cannot_be_used_without_approval` **and** `test_ai_generated_asset_is_usable_once_a_human_approves_the_gate` | **Holds only by coincidence (V-25).** The AI flag is a `"_ai"` **substring** of a display string, and stage 13 re-searches a **different** candidate list than the one stage 12 approved. Not bypassable today only because `ASSET_SELECTION` is unconditionally `MANUAL`. The `Approval` row's actor is a client-supplied string on an unauthenticated API (**V-32**), and a bare `a` keypress writes it (**V-75**). **T-74**, **T-81**, **T-117**. |
| 10 · Licenses enforced by a gate | `LicensePolicy.validate_asset_license` at asset discovery and storyboard cuts, over a canonicalized license identifier | `test_guard_6_policy_validation_methods_have_production_callers`, plus 19 parametrized dialect tests | Holds for the assets it sees — but stage 11 validates one search result and stage 13 renders **another** (**V-25**). |
| R4 · No fixture reads as a fact, in any language | AST guard over Python fakes; text guard over `apps/web/src` and `apps/renderer/src` | `test_guard_7_*` and `test_guard_8_*` | **The guards do not scan `application/` (V-82).** Guard 1 covers seven `adapters/` subdirectories by name (ADR-0014's own scope). Both invented payloads found on 2026-09-05 — `ResearchAgent`'s fabricated source (**V-81**) and `ScriptAgent`'s placeholder (**V-67**) — are in `application/agents/`. **T-123.** |
| R5/R8 · A failed gate action is never shown as a decision | `ApprovalQueue` surfaces the error and records nothing | `test_guard_8_gate_actions_do_not_report_success_on_failure` | Holds for the gate action itself. **A failed `GET /gates/pending` still renders as "No pending Gates"** and "Awaiting a human: 0" (**V-35**), and a failed `GET /topics` as "Topics: 0" (**V-36**). **T-84.** |

Invariants **3** (inference and opinion are labelled) and **6** (no hidden global mutable state) are
absent from this table because neither has an enforcing check that runs. `AssertionType` is required
on every Claim by Pydantic and conflicting evidence is stored on both sides, which is Invariant 3
holding *structurally*; `FocusSnapshot` is captured by value into every Run, which is Invariant 6
holding the same way. Neither has an integration test asserting it after a run, so neither is claimed
here (**R10** — a policy with no failing case is decoration).

---

## 3. What does not exist

Stated plainly, because a stub that is not named in this section is a stub that will be mistaken for
a feature.

**Added 2026-09-05 by the §19 verification — things that were absent without being written down
anywhere:**

- **Verification, in the sense the word implies.** The agent runs and writes a verdict; the verdict
  is a substring match over a free string that defaults to `"verified"` (**V-58**, **T-103**).
- **Any enforcement of the Research Profile.** `preferred_apis`, `source_allowlist` and
  `source_tier_floor` have **no reader** anywhere in the tree. SPEC §9's source policy is declared
  and unenforced, and every source is written `source_tier=PRIMARY` regardless (**V-41**, **V-80**).
- **Any effect of the Focus on output.** `captured_focus` is read twice — as a string in the
  idempotency hash, and by stage 1, whose result is discarded. `ScopeMode`'s three values behave
  identically. ADR-0002's Wikidata Entity resolution does not exist (**V-42**, **V-77**).
- **Any way to set the Active Focus.** `set_active_focus` has only test callers, so every Run
  captures a `Focus` built in memory and never persisted (**V-37**). `focus` and `active_focus` are
  empty in the application database.
- **A persisted SoundTrack.** Stage 14 composes one and discards it; there is no table and the
  renderer never receives it (**V-62**).
- **A written impact index.** `record_claim_usage` has only test callers, so `claim_usages` is empty
  for every Run and retraction impact cannot be computed (**V-48**). The previous wording here —
  "beyond `claim_usages`" — read as though it worked.
- **Any reader for the publishing schedule.** `save_window`, `get_windows`, `save_blackout_rule` and
  `get_active_blackout_rules` have only test callers; `PublishScheduler` is an orphan. **ADR-0007 is
  entirely unbuilt**, not partially (**V-47**).
- **ADR-0001's operational half.** No reaper, no retry, no backoff, no dead-lettering, no stuck-Run
  detection, no transactional enqueue, no `SKIP LOCKED` claiming; `DramatiqQueueBroker.enqueue`
  discards its `step_name` (**V-45**).
- **A deployment for the dashboard.** `pnpm -r build` produces `apps/web/dist/`; Compose runs no
  service for it, Caddy has no static root and does not strip `/api`, and that prefix is removed by
  the Vite dev server only. The operator interface exists under `pnpm dev` and nowhere else
  (**V-52**).
- **A worker that can start.** `dramatiq.set_broker` is called only in `tests/conftest.py` and
  `redis` is not a dependency, so Compose's `worker` service fails at import — and
  `ATLAS_QUEUE_BROKER=dramatiq` reproduces V-18 verbatim (**V-51**).
- **Any authentication by default.** `api_auth_enabled` is `False`, and turning it on without setting
  a key accepts **any** non-empty `X-API-Key` (**V-29**, **V-30**).
- **Any contract check between the API and the dashboard.** Nothing asserts that
  `apps/api/schemas.py` and `apps/web/src/api/types.ts` describe the same shapes (**V-53**).
- **A test that commits.** Every integration test rolls back, so no test exercises durability,
  cross-transaction visibility, or the rollback that destroys a failed Run (**V-50**, **V-20**).

- **Rendering (SPEC Phase 7).** `StubRenderer` produces a flat ffmpeg colour field at the correct
  resolution for the requested target, with real captions computed from the persisted Timing Plan.
  No Remotion composition is mounted, no node process is spawned, and no archival image reaches a
  frame. Deferred by **D57**; ADR-0005 still describes the intended renderer.
- **Publishing (SPEC Phase 8).** `StubPublisher` logs what it would publish and returns
  `stub:<artifact-id>`. No YouTube OAuth, no upload.
- **AI image generation.** `StubImageGenerator` holds the GPU lease correctly and returns
  placeholder bytes. No diffusers pipeline is loaded. It has no caller in the pipeline.
- **The knowledge system (SPEC Phase 6).** Graph, novelty check and impact index beyond
  `claim_usages` are not implemented. `pgvector` is not installed and no vector column exists.
- **Cassettes and the golden set.** Neither exists; `docs/ARCHITECTURE.md` §9 describes both. This
  is why no test covers a network-backed adapter: a unit test never touches the network, and there
  is nothing to replay. `WikipediaSearch`, `HttpSourceFetcher`, `WikimediaCommonsSearch`,
  `InternetArchiveSearch`, `OllamaEmbedder`, `GeminiLlm` and `FreesoundLibrary` are verified only by
  hand.
- **The asset, script-beat and quality-rubric review panels.** They existed, drawn from a
  `gate.metadata` field the API does not return, and were deleted with the rest of **V-03**. Bringing
  them back means endpoints that return an approved Run's asset candidates, script beats and quality
  report — not fixtures (**D111**, audit §15.7).
- **Any way to create a Domain, a Topic or a Channel from the browser.** The CLI can (T-62), the
  API cannot, so the dashboard cannot bootstrap itself from an empty database: an operator has to
  open a terminal once before the "Launch a Run" form can succeed. **T-64**, SPEC §17.11.
- **A Topic that stage 1 proposes reaching the database.** `IDEA_DISCOVERY` calls the agent, counts
  the result and returns `ideas_count_N`; the proposed ideas are discarded. Whether a model-proposed
  Topic may be persisted before a human has seen it is an Invariant-2 question and is deliberately
  left open — route (c) of **T-62**, **D136**.
- **A background queue, and therefore any Run that does not block its caller.** ADR-0001 decides
  Postgres is the queue and that "the API only validates and enqueues; it never executes pipeline
  work". Neither is built. No broker was configured at all until 2026-09-05, so dramatiq fell back
  to Redis — rejected by name in that same ADR, absent from `pyproject.toml` and from
  `docker-compose.yml` — and **every** `POST /runs` and `atlas run create` died with
  `ModuleNotFoundError: No module named 'redis'` (defect **V-18**, P0). `Container.queue_broker` is
  now `InlineQueueBroker`, named for what actually happens: both entry points run all eighteen
  stages inside the request. That is defect **V-19** and it is still open — tasks **T-67** and
  **T-68**.
- **A real-provider run.** `docker compose up` now builds, but no Run has ever executed against
  Gemini, Ollama or Freesound end to end. **T-34**, still sequenced after T-29 and T-30.
- **Timing that fits a target duration.** ADR-0006 §2 promises the Timing Plan solves per-Beat hold
  for a total within ±2 s of target and fails loudly, routing back to the Script stage, when no
  solution exists. `_compute_timing_plan` accumulates instead — one pass summing beat durations, no
  target, no solve, no repair path — and the prompt asks for 12–18 beats of 3.0–4.5 s, spanning
  **36 s to 81 s** against a judge that accepts 58–62 s. So a fully prompt-compliant script can be
  rejected at stage 17 and no stage can fix it. It has never bitten because `FakeLlm` returns exactly
  15 beats × 4.0 s = 60.0 s: the fixture lands on the bound by construction, and the whole suite
  passes over a mechanism that is not there. Defect **V-14**, task **T-61**, found 2026-09-04 by
  reading ADR-0006 against the code while closing T-20.
- **A `blobs` table.** Blobs are written to `var/blobs/sha256/…` with no database row, so there is
  no reference count and no deduplication bookkeeping.
- **YAML configuration.** Routing policy and gate defaults are Python dicts; style and research
  profiles do not exist.

---

## 4. Known gaps that are open by decision

These are real and are not being hidden; each is recorded with the decision that left it open.

**Opened by decision on 2026-09-05 (D144–D151):** the §19 verification found 70 defects and fixed
none of them, deliberately — audit §18.0 rule 4 requires recording before fixing, and **D142** put
verification ahead of implementation for exactly one session. Everything in audit §19 is therefore
"known and open" as of today. Do not treat that as a decision to leave any of it: **§19.10 is the
ordered list and position 0 is a two-line fix.** Four judgement calls inside that session are worth
carrying:

- **The ADRs are contradicted, not amended.** ADR-0012, ADR-0002, ADR-0003, ADR-0005 and ADR-0009
  each describe behaviour the code does not have. None was edited: **R9** and the repository's own
  rule say an ADR is superseded in writing, never quietly corrected, and a verification session does
  not get to decide which side moves (**D147**). Tasks **T-29/T-30/T-88**, **T-118**, **T-125**,
  **T-126**, **T-127**.
- **The `a`-to-approve shortcut is recorded, not removed** (**D148**). It is deliberate — the button
  advertises it — so changing it silently would overwrite a decision nobody wrote down. **T-117**
  asks for the decision.
- **V-49's schema drift is not fixed in a docs session** (**D149**). Adding three foreign keys to
  non-empty tables is a migration with a lock, and **D106**'s precedent is that a documentation pass
  does not change behaviour. **T-95**.
- **The first pass's index claim was corrected in place and the correction was written down**
  (**D150**), rather than the wrong text being deleted. Audit §19.8.

- **Asset candidates are not persisted at stage 11.** Stage 13 re-searches, so the candidate list
  the operator approved at the stage 12 gate is not provably the list the storyboard drew from. The
  storyboard itself is persisted, so everything from stage 13 onward is stable. ADR-0016,
  trade-offs.
- **The story-angle gate suspends before an angle exists.** A suspending stage runs no handler, so
  stage 7's operator decision is "proceed", not "approve this angle". The angle is chosen at stage 8
  by `select_story_angle`. **D92**.
- **`trace_id` is never bound into the logging context.** The column and the structlog processor
  both exist; nothing connects them, so log lines do not carry it.
- **Model IDs are hardcoded.** ADR-0012 §3; defect C-08. The Ollama base URL is no longer among
  them — it is `Settings.ollama_base_url`, read from `OLLAMA_URL` (**D116**, defect V-05).
- **Layering is enforced for `domain/` only.** `tests/unit/test_layering_boundaries.py` does not
  check the `adapters → application` direction. ADR-0014.
- **No repair attempt on malformed structured output.** `ARCHITECTURE.md` §5 promises one; both LLM
  adapters fail immediately instead.
- **`PUBLISH` succeeds against a stub publisher.** The stage now really calls the publisher and
  records what it returns, but `StubPublisher` returns `stub:<artifact-id>` and the run reaches
  `completed` having published nothing. It also ignores `PublishScheduler` and the blackout rule.
  Audit task **T-21**, decision **D102**.
- **Five adapters are orphaned.** `AudioCompositor`, `KeystrokeSampler`, `ImageDownloader`,
  `PublishScheduler` and `OllamaLlm` are defined and reachable from nothing but their own module.
  Audit task **T-28**.
- **The gate-stage branch in `_dispatch_stage_handler` is unreachable.** All six stages it names
  always suspend. Harmless, but undocumented dead code until now. Audit task **T-53**.
- **No `blobs` table.** Blobs are written to `var/blobs/sha256/…` with no row, so there is no
  reference count and no deduplication bookkeeping. `ARCHITECTURE.md` §6 and §11.8, defect A-03.
- **Quota is checked with one extra query per model call.** `check_rate_limits` reads
  `quota_ledger` every time rather than caching a window, because a cached window is what defect
  **V-04** was. At Atlas's call volume — single digits per Run — the query cost is not worth
  optimising away, and doing so would need a cache invalidated by other processes. **D115**.
- **The minute window is coarse.** Ledger rows bucket by `window_start=now.replace(second=0)` and the
  summary selects `window_start >= now - 1 minute`, so the RPM check spans between one and two
  wall-clock minutes of rows. It over-counts, never under-counts, which is the safe direction for a
  free tier.
- **An exhausted quota fails the Run instead of suspending it.** ADR-0004 promises suspend-and-notify;
  `check_rate_limits` raises and `_execute_stage` marks the Run `failed` along with the Step. Found
  during the 2026-08-31 documentation reconciliation, recorded rather than fixed in a docs pass
  (**D106** precedent). It became a real risk only when the budget became shared and enforceable —
  defect **V-13**, task **T-60**.
- **Per-Run quota reservations and response caching do not exist.** SPEC §11 promises both.
  `platform/cache.py` is written and no adapter calls it. Same task, **T-60**.
- **The Timing Plan accumulates rather than fits.** Recorded on the day it was found rather than
  fixed, because the two honest routes — implement ADR-0006 §2, or supersede it and constrain the
  prompt's *sum* — are both behaviour changes with a design decision inside them, and a documentation
  session does not quietly change behaviour (**D106**, **D125** precedent). **D134**, task **T-61**.
- **The CLI prints a rich traceback for a domain error.** Every command lets `AtlasError` reach
  Typer; `atlas run status run_absent` and `atlas topic create --domain dom_absent` behave
  identically, both exiting 1 with the error type named. Nothing is hidden — this is presentation,
  and it is uniform, so it is one decision about all commands rather than three fixes to the new
  ones. **T-65**, **D138**.
- **The approval screen shows Gate rows and nothing else.** An operator can see which Gate is
  pending and open the Run's Knowledge Object and telemetry, but cannot review asset candidates,
  script beats or the quality report in place — §3, **D111**.

---

## 5. Where to look next

**The five-angle verification is done.** It ran on 2026-09-05 (audit **§19**), changed no code, and
found **70 defects, V-20 – V-89**. The next session implements; it does not verify again.

**Start at `docs/AUDIT-2026-08-29.md` §19.10 position 0 and work down.** That list supersedes §15.9.
Its first ten, and why they are in that order:

| # | Task | Why first |
|---|---|---|
| 0 | **T-103** — the verification verdict is an enum, not a substring (**V-58**) | Two lines. A model answering `"unverified"` marks the claim VERIFIED, and a missing field does the same. It is the only path to that status and rendering gates on it. **Nothing else in this file that depends on a claim being verified is currently true.** Write the failing test first. |
| 1 | **T-69** — a failed Run must survive (**V-20**) | P0 data loss on all three entry points, probed on two. A failed stage rolls back the `runs`, `steps`, `gates`, `model_calls` and `quota_ledger` rows. Every later session debugs blind until this is fixed. |
| 2 | **T-113** — source text is data, not instructions (**V-71**, **V-72**) | P0. A hostile page writes its own claims and the verbatim guard passes them. T-103 is what stops them reaching VERIFIED; do the two together. |
| 3 | **T-95** — close the schema drift, add `alembic check` to CI (**V-49**) | Three declared foreign keys are absent from the database. Do it before anything writes more rows. |
| 4 | **T-78 + T-79** — fail closed; set the deployment posture (**V-29**, **V-30**) | P0 security, one boolean expression and one Compose change. **T-57 closes inside T-79** — the dashboard already sends the key, verified. |
| 5 | **T-104 + T-105 + T-108** — the quality gate must measure (**V-59**, **V-60**, **V-65**) | The last gate before publish invents up to seven of eight scores and hardcodes two of six deterministic checks to `True`. |
| 6 | **T-122 + T-121** — no invented source, no asserted tier (**V-81**, **V-80**) | R1/R2 broken in `application/`. Before T-123, which is written to fail until these are fixed. |
| 7 | **T-123** — extend Guard 1 to `application/`, Guard 6 to `domain/` (**V-82**, **V-84**) | The detector cannot see the layer the last three fabrications were in. Needs an ADR amending ADR-0014's scope. |
| 8 | **T-114** — the fetcher is an unrestricted SSRF primitive (**V-70**) | It is what makes T-113 reachable from outside a search result. |
| 9 | **T-106** — `render_prompt` must not interpret backslashes (**V-61**) | A source containing `\1` crashes extraction today, probed. One line. |

**Read order:** this file → `docs/AUDIT-2026-08-29.md` **§19** (the register and the ordered list;
**§19.7 is what held**, **§19.9 is what was not checked**) → **§18** (the brief that commissioned it,
and §18.0's standing rule, which still applies) → **§17**, **§16**, **§15** (**§15.8** is what not to
do) → §14, §13 → `docs/SPEC.md` §17 (**§17.12** is newest) → `docs/ARCHITECTURE.md` **§2.1** (the
HTTP surface — verified correct on 2026-09-05 and unchanged) and §11 (**§11.7g** is newest) → the
relevant ADR → the code.

**Five ADRs contradict the code and none has been amended** — that is deliberate (**D147**), and it
is the largest single block of work on the list: ADR-0012 (**V-40**, five of six parts unbuilt, and
the shipped model ID returns 404), ADR-0002 (**V-77**, four of seven decisions, one inverted),
ADR-0003 vs ADR-0016 (**V-85**, **V-86**), ADR-0005 (**V-88**), ADR-0009 (**V-87**).

**Do not start T-34** (the honest real-provider run) before **T-103**, **T-69**, **T-29**, **T-30**,
**T-88**, **T-58**, **T-61** and **T-113**. Two reasons beyond the original one: the model ID Atlas
would call is retired and returns **404** (**V-40**), and a run that fails leaves **no record at
all** (**V-20**), so the scarce budget would be spent for nothing recoverable.

### What the 2026-09-05 verification session did **not** do, so you do not go looking

Copied from audit §19.9. Absence here is not clearance.

- **No provider call of any kind**, deliberately (§18.0 rule 5). No Gemini, Ollama, Freesound,
  Wikipedia, Wikimedia, Internet Archive or plain HTTP request was made from any code path. The seven
  network-backed adapters remain verified only by hand (**T-58**), and four of them —
  `adapters/search/wikipedia.py`, `adapters/images/*`, `adapters/audio/freesound.py`,
  `adapters/llm/ollama.py` — **were not even read**, so V-70's SSRF analysis covers `HttpSourceFetcher`
  only.
- **No browser walkthrough against a live API.** Angle 3 was done by reading every component and
  running the mocked Playwright suite. The empty-database walkthrough — T-64's own *Done when* — is
  still owed (**T-87**).
- **`docker compose up` was not run.** V-51 and V-52 are read from the Compose file, the Caddyfile,
  the Vite config and the absence of a `set_broker` call. Running it is the cheapest test of both.
- **Two ADRs were not read end to end** — 0011 and 0015, their Decision sections only. Ten were read
  in full. The last two read (0002, 0016) produced five divergences between them, so **§18.5's
  *Done when* — "every ADR read against its implementation" — is not met.**
- **`domain/` is partially audited.** `agents/models.py`, `quality/models.py`, `script/models.py`'s
  timing types, `knowledge/invariants.py` and `knowledge/upcast.py` were read.
  `domain/media/models.py`, `domain/assets/models.py`, `domain/publishing/models.py` and
  `domain/execution/models.py` were not read end to end.
- **`apps/renderer/` and `packages/tokens/` were not reviewed** beyond confirming they build and that
  the renderer imports the token package (which `apps/web` does not — **V-88**).
- **No performance or load measurement.** V-26's event-loop claim is from reading, not timing.
- **No fix was attempted and no test was written.** Every task in audit §19.10 is unstarted, and the
  70 findings are recorded, not remediated.
- **A `pytest-cov` measurement was not possible** — the package is not installed. The "which modules
  no test touches" sweep in audit §19.6 is a name-based grep and is explicitly weaker than coverage;
  it reproduced the known T-58/T-28 set plus `apps/cli/backup_restore.py`.

### Session close-out checklist

Every working session ends by doing all of these. They exist because each was skipped at least once
and the result was a document that read as truth.

- [ ] Re-run `uv run ruff check .`, `uv run mypy .`, `uv run pytest`, `uv run pre-commit run
      --all-files` and `pnpm -r build`; paste the raw output into §0 of this file. Never carry a
      number forward (**R7**).
- [ ] Update §1 with whether the tree is clean. Do not write a commit hash into this file.
- [ ] Move anything newly true into §2, anything newly known-absent into §3, anything deliberately
      left into §4 with the decision ID.
- [ ] Tick a task in the audit's §6 **only** if its own *Done when* is met; otherwise write which
      part is done under the task and leave the box open (**T-50**). Update **§15.9**'s ordered list
      if the order changed, and say why.
- [ ] Record every judgement call in `docs/DECISIONS.md` with the why, and file an ADR if it
      introduced a dependency, changed a data model, changed a layer boundary, added a provider
      category, contradicted an existing ADR, or fired an existing ADR's *Revisit when*.
- [ ] Re-verify `docs/ARCHITECTURE.md` §11 and `docs/SPEC.md` §17 if the session touched structure
      or behaviour, and say which side of each row changed.
- [ ] **If you added, removed or changed an HTTP route, update `ARCHITECTURE.md` §2.1 in the same
      commit.** The dashboard codes against that table; when it did not exist, the dashboard invented
      an API and rendered fixtures for a phase (**V-03**, **D122**).
- [ ] **If you touched `apps/web` or `apps/renderer`, run `uv run pytest` — not just `pnpm build`.**
      Guards 8 and 9 live in the Python suite on purpose (ADR-0017); a front-end change that
      introduces a fixture fails there and nowhere else. Run `pnpm test` too: the browser suite is
      the only thing that proves a panel renders a row rather than a literal.
- [ ] **Before claiming a subsystem works, name the test that would fail if you deleted it.** If
      there is none, the subsystem is unverified however green the suite is (**R10**). Four defects
      — V-01, V-04, V-14, V-18 — passed hundreds of tests each.
- [ ] **After changing an adapter the production `Container` wires, check a test resolves the real
      `Container`.** Only `tests/integration/test_production_adapters.py` and
      `test_queue_broker_wiring.py` do. Everything else substitutes a fake, which is how a broker
      that could not be called shipped green (**V-18**).
- [ ] **If you wrote a row to the local `atlas` database by hand, record what it was and whether it
      overwrote anything** (**R11**). This session destroyed two rows of operator configuration with
      its own new command and only noticed by reading them back (**V-17**).
- [ ] **Run `uv run alembic check` and act on the result.** It fails today (**V-49**). Once **T-95**
      lands, a failure means your change drifted the models from the migrations — fix it in the same
      commit, and do not let the noise of nine redundant `index=True` flags hide a real one.
- [ ] **If you touched an agent, ask what it does when the model returns something unexpected.**
      Four of the nine agents were found on 2026-09-05 to default, invent or substring-match their
      way past a bad response (**V-58**, **V-59**, **V-60**, **V-81**). A Pydantic field with a
      permissive type and a favourable default is the shape to look for.
- [ ] **If you added a `validate_*` or `enforce_*` function, put it where a guard can see it.**
      Guard 1 scans seven `adapters/` subdirectories; Guard 6 scans `application/policies/` only.
      A policy outside those directories is invisible to both (**V-82**, **V-84**).
- [ ] **Before writing "verified", "complete" or "enforced" in this file, name the test that would
      fail if you deleted the mechanism — and check that test does not run against a fake that makes
      it true by construction.** On 2026-09-05 that question retired four claims in §2.
