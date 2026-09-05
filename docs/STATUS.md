# Status

**Last updated:** 2026-09-05 (V-15 – V-19 found by operating the system; T-62, T-63, T-64 and T-66 closed)
**Branch:** `docs/audit-2026-08-29` — see §1.

This file separates **decided** from **done**. Everything else in `docs/` records what Atlas *will*
be; this records where it actually stands. It is rewritten from measurement at the end of every
working session, and **every number in it comes from a command run in the session that wrote it**
(rule R7). The previous body is archived unchanged at
[`docs/archive/STATUS-2026-08-29.md`](archive/STATUS-2026-08-29.md); nothing in that file is a
current claim.

---

## 0. Measured baseline

Measured on 2026-09-05, in the session that wrote this section, after the T-62, T-63, T-64 and V-18 changes.
**Re-run them before quoting them** (**R7**).

```
$ uv run ruff check .
All checks passed!

$ uv run mypy .
Success: no issues found in 179 source files

$ uv run pytest --tb=short
191 passed in 21.63s

$ uv run pre-commit run --all-files
Ruff Lint Check / Ruff Format Check / Anti-Fabrication Structural Guard — Passed

$ pnpm test
10 passed (4.3s) — apps/web/e2e/dashboard.spec.ts, Playwright Chromium

$ pnpm -r build
packages/tokens · apps/renderer · apps/web — 3 of 3 built

# 2026-09-05, same session:
$ ls .../alembic/versions/*.py | grep -v __init__ | wc -l
7 migrations on disk

$ uv run python -c "from atlas.adapters.persistence.tables import Base; print(len(Base.metadata.tables))"
30 tables

$ uv run python -c "from apps.api.main import app; print(len(app.openapi()['paths']))"
15 paths, 20 operations — transcribed in ARCHITECTURE §2.1
```

`alembic upgrade head` **was** run against the `atlas` database this session — it is how the API and
the dashboard were brought up, and it is where `topics` was found empty (defect **V-15**). The 7 and
the 30 above are still counted from the migration files and from `Base.metadata` rather than from a
fresh apply, which is a weaker measurement, and is written down as such rather than carried forward
as if it were the stronger command (**R7**). CI runs the real `alembic upgrade head` on every push.

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

**Phase 1 · Architecture** — complete. Spec, architecture, glossary, ADRs 0001–0018.

**Phase 2 · Database** — complete. 30 tables, 7 Alembic migrations, round-trip tested
(`test_alembic_migrations_roundtrip` applies head → base → head). Knowledge Objects are
row-per-version with a separate current pointer (ADR-0003). Claims are append-only: an immutable
identity row plus `claim_versions`, each version carrying the actor and the reason (ADR-0015).

**Phase 3 · Backend** — complete. FastAPI, Dramatiq worker, the 18-stage Run/Step state machine,
gates, approvals, resource locks, idempotency keys and the quota ledger. A Run traverses every stage
against fakes, suspends at each of the six manual/hybrid gates, and resumes.

**Phase 4 · Frontend + CLI** — CLI parity is real and tested. The dashboard (`apps/web`) builds and
now reads the API: Runs, pending Gates, quota, and two endpoints added in this session
(`/runs/{id}/knowledge`, `/runs/{id}/telemetry`). Every panel renders a database row or an error —
until 2026-08-31 five of its components rendered invented claims, invented snapshot hashes and an
invented telemetry feed, and its API client answered an unreachable backend with fabricated Runs and
a fabricated passing quality report (defect **V-03**, audit §15.4). **Browser testing is real and verified
via Playwright** (task **T-55**, **ADR-0018**): `apps/web/e2e/dashboard.spec.ts` executes in headless Chromium,
asserting that the dashboard renders live API topic IDs, gate step IDs, error banners on failed actions,
and real snapshot hashes without fixtures.


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

**A Timing Plan can no longer overstate its own duration (T-20, D129).**
`TimingPlan.total_duration_seconds` was a plain field defaulting to `60.0`; a plan carrying 3.5
seconds of beats reported a full minute and satisfied the judge's 58–62 s deterministic check for
free. It is now a computed field derived from the last beat's end time, so the stated duration
cannot disagree with the timeline behind it. `tests/unit/test_timing_plan_duration.py` asserts the
derivation, asserts that a caller passing `60.0` still gets `3.5`, and asserts that the judge
rejects the short plan — the last of which failed with `duration_bounds is True` before the change,
which is defect **R-04** reproduced. **What this does not do is make the duration correct**, only
honest: nothing steers a Script towards 60 s. See §3 and defect **V-14**.

**Phase 5 · Agents** — complete. Topic discovery, research, extraction, verification, story angle,
script, storyboard, sound design and quality judge. An ORIGINS Topic yields a source-traced
Knowledge Object and a Script whose every beat cites verified claims. **Topic title resolution is
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
artifacts exist for both aspect ratios with WebVTT captions carrying real cues; publication ran once
per artifact; every `model_calls` row records `provider='fake'`, the adapter that actually ran; the stage 1 topic
discovery call and both stage 13 embedding calls are metered with matching `quota_ledger` entries in
the minute and day windows.

### 2.1 Phase numbering — SPEC §15 is the numbering (D58, T-38)

This file used to number phases differently from `docs/SPEC.md` §15 and then declared the renumbered
phases complete. It now uses SPEC's numbering. The table maps the old STATUS names onto it so the
work is recounted rather than lost.

| SPEC §15 phase | What it means | Old STATUS name | State |
|---|---|---|---|
| 1 · Architecture | Spec, architecture, glossary, ADRs | Phase 1 (Architecture) | **complete** |
| 2 · Database | Schema, migrations, KO versioning, repositories | Phase 2 (Database & Persistence) | **complete** |
| 3 · Backend | FastAPI, worker, Run/Step state machine, gates, quota | Phase 3 (+ 3.1 remediation) | **complete** |
| 4 · Frontend + CLI | Dashboard shell, approval queue, CLI parity | Phase 4 (Frontend + Remotion Renderer) | **CLI complete. Dashboard reads the API and renders no fixtures, but no test drives a browser (T-55) and the approval queue cannot show the artifact under review (T-59).** The renderer half of the old name was never Phase 4 work. |
| 5 · Agents | Research, extraction, verification, script, judge | Phase 5 (Agents & Intelligence Engine) | **complete** |
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

| Invariant | Enforced by | Proven by |
|---|---|---|
| 1 · No fact without a source | `validate_knowledge_object_claims_are_traceable`, called by `KnowledgeRepository.save_version` before any write | `test_no_claim_reaches_output_without_evidence` |
| 1 · Verbatim evidence | `ExtractionAgent` rejects any quote not present in the snapshot | `test_every_evidence_quote_is_verbatim_in_its_snapshot` |
| 1 & 2 · Pre-render backstop | `PipelineRunner._assert_script_claims_are_traceable` on the persisted script | the end-to-end assertions above |
| 2 · A model is never the source | Claims start `unverified`; only `VerificationAgent` may promote them | `test_claim_is_not_verified_at_extraction_time` |
| 4 · Append-only knowledge | `claim_versions`; `save_claim` inserts, never updates | `test_claim_state_changes_append_a_version_and_never_overwrite` |
| 5 · No provider SDK outside its adapter | AST guards 1–4 over `adapters/` | `tests/unit/test_no_fabrication.py` |
| 7 · Every artifact records how it was made | `model_calls` provenance taken from the adapter that executed; production artifacts persisted | `test_model_call_provenance_matches_the_adapter_that_ran` |
| 8 · Every model call is metered | Every agent holding an LLM or Embedder port takes a `QuotaManager`; `check_rate_limits` reads `quota_ledger` | `test_guard_9_every_agent_that_calls_a_model_holds_a_quota_manager`, `tests/integration/test_quota_enforcement.py`, and the end-to-end assertions on `topic_discovery_v1` and `embedding_v1` |
| 9 · AI imagery needs human approval | An `Approval` row on the asset-selection gate, resolved by step ID | `test_ai_generated_asset_cannot_be_used_without_approval` **and** `test_ai_generated_asset_is_usable_once_a_human_approves_the_gate` |
| 10 · Licenses enforced by a gate | `LicensePolicy.validate_asset_license` at asset discovery and storyboard cuts, over a canonicalized license identifier | `test_guard_6_policy_validation_methods_have_production_callers`, plus 19 parametrized dialect tests |
| R4 · No fixture reads as a fact, in any language | AST guard over Python fakes; text guard over `apps/web/src` and `apps/renderer/src` | `test_guard_7_*` and `test_guard_8_*` |
| R5/R8 · A failed gate action is never shown as a decision | `ApprovalQueue` surfaces the error and records nothing | `test_guard_8_gate_actions_do_not_report_success_on_failure` |

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

**Read order for the next session:** this file → `docs/AUDIT-2026-08-29.md` **§17** (the 2026-09-05
session; defects **V-15** and **V-16**, both found by using the system rather than by reading the
register) → **§16** (the 2026-09-04 session; it carries defect **V-14**) → **§15** (what the second 2026-08-31
verification found; **§15.9** is the live ordered work list, kept current, and **§15.8** is what not
to do) → §14 and §13 for the sessions before → `docs/SPEC.md` §17 (**§17.11** is newest) →
`docs/ARCHITECTURE.md` **§2.1** (the HTTP surface — the contract the dashboard codes against) and §11
(**§11.7e** is newest) → the relevant ADR → the code.

`docs/AUDIT-2026-08-29.md` is the authoritative register of what is broken. **§15.9 supersedes §14.2**
as the ordered list. Its first three, in short:

1. **T-61 — fit the Timing Plan, or amend ADR-0006.** Defect **V-14**, found 2026-09-04. The plan
   accumulates where the ADR promises fitting; prompt-compliant scripts span 36–81 s against a
   58–62 s gate with no repair path. **Do this before T-34** — the first real-provider run is exactly
   where that spread meets that gate, on a 20-request daily budget. It was displaced by T-62 and
   T-63 on 2026-09-05 for the reason **D135** records: it is a defect inside a Run that no operator
   could start.
2. **T-53 — the unreachable gate-stage branch.** Decide and document.
3. **T-57 — consistent auth dependency on the API.** Two routes are missing `verify_api_key` —
   `GET /runs/{id}/steps` and `GET /runs/{id}/gates`, verified route by route on 2026-09-04.
4. **T-64 — HTTP equivalents for the three catalogue commands.** New 2026-09-05; until it lands the
   dashboard cannot bootstrap itself.

**Do not start T-34** (the honest real-provider run) before **T-29**, **T-30** and now **T-58**. The
Gemini free tier allows 20 requests a day and a correct run needs 6–9; that scarcity is the direct
cause of the 2026-08-29 fabrication incident. Re-tiering onto Ollama first is what makes the attempt
survivable, and cassettes are what make a failure inside a network adapter debuggable rather than a
second session.

### What this session did **not** do, so you do not go looking

- **No real-provider run.** No Gemini, Ollama or Freesound call was made from the pipeline. Stage 1
  was spending Gemini quota unmetered until **V-02** was fixed, so `quota_ledger` cannot tell you
  today's remaining budget — start T-34 from a re-measured ledger, not from the table in §0.
- **Ollama is not running on this machine.** `OllamaEmbedder` fails at stage 13 against a live
  container unless the daemon is up. The URL is configuration now (`OLLAMA_URL`), so point it at
  wherever the daemon actually is.
- **`docker compose up` was never run to completion.** `docker compose config` validates and the
  `Dockerfile` is new and unbuilt. Expect to debug the image once, not to have it work first try.
- **`alembic upgrade head` was not run locally against a fresh `atlas` database.** §0 says which
  weaker commands produced the 7 and the 30 instead. CI runs the real thing.
- **No verification pass.** The registers were reconciled against the code — narrower than audit
  §15's re-measurement, which was not repeated. `ARCHITECTURE.md` §2.1 *was* re-checked against
  `app.openapi()` route by route, including the auth column.
- **V-14 was found, not fixed.** See §4 and **D134**. It is still task **T-61**, now third behind
  the queue defects.
- **No Run was created through the fixed path.** The enqueue was the last thing between a request
  and stage 1, which calls Gemini for real — 6–9 requests against a 20-a-day budget, on a pipeline
  that can still be rejected at stage 17 (**V-14**). That is **T-34** and it is an operator
  decision, not a verification step. The broker fix is covered by
  `tests/integration/test_queue_broker_wiring.py`, which calls the broker the production container
  actually resolves.
- **No Run was created against real providers**, deliberately. The Topic that was created by hand
  makes `POST /runs` succeed now, and succeeding means stage 1 spends Gemini quota — that is
  **T-34**, and it stays sequenced behind T-29, T-30 and T-58.
- **No HTTP route was added or changed**, so `ARCHITECTURE.md` §2.1 is untouched and still lists 11
  paths / 12 operations. Only exception handlers were added.
- **CI is blocking but not unbypassable.** `enforce_admins` is false; an administrator can override
  the required check.

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
      introduces a fixture fails there and nowhere else.
