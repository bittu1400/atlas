# Status

**Last updated:** 2026-08-31 (independent verification session, then a documentation reconciliation pass)
**Branch:** `docs/audit-2026-08-29` — see §1.

This file separates **decided** from **done**. Everything else in `docs/` records what Atlas *will*
be; this records where it actually stands. It is rewritten from measurement at the end of every
working session, and **every number in it comes from a command run in the session that wrote it**
(rule R7). The previous body is archived unchanged at
[`docs/archive/STATUS-2026-08-29.md`](archive/STATUS-2026-08-29.md); nothing in that file is a
current claim.

---

## 0. Measured baseline

Measured on 2026-08-31, in the session that wrote this section, on the tree of commit `714cade`
(`fix(pipeline): persist production artifacts…`). The commits after it change documentation only —
`git diff 714cade..HEAD --stat -- ':!docs' ':!*.md'` shows the test rename and nothing else — so the
three numbers below still hold. **Re-run them anyway before quoting them** (**R7**).

```
$ uv run ruff check .
All checks passed!

$ uv run mypy .
Success: no issues found in 158 source files

$ uv run pytest --tb=no
122 passed in 13.08s
```

On 2026-08-31 there are **no `xfail` markers left in the suite**. Every guard that previously stood
as a known-failing marker — Guard 2 (fakes in the production container), Guard 4 (stubs wearing real
provider names), the STATUS honesty check, and the renderer-provenance test — now asserts a
behaviour that holds.

**CI has still never run a single check.** `gh run list` on 2026-08-31 shows two runs, both
`failure`, both from 2026-08-26, both predating the `uv sync --all-extras` fix. `ci.yml` triggers
only on push to `main` or a pull request into `main`, and the branch `docs/audit-2026-08-29` has
never been pushed. Closing **T-00** and **T-11** needs an operator to push (D82). The numbers above
were produced locally and nothing has independently verified them.

---

## 1. Working tree state

The working tree is clean on branch `docs/audit-2026-08-29`. Commit `714cade` carries the 2026-08-29
Stage C work — which had never been committed, despite audit §12.3 claiming it was — together with
this session's B1–B9 remediation; the commits after it are documentation, plus one test rename
(**D107**). The false "committed and clean" claim is recorded as finding **A1** in audit §13.

This file deliberately no longer names its own HEAD. A document that states the hash of the commit
containing it is wrong the moment it is committed, and the last two sessions each produced a
follow-up commit whose only purpose was to correct that hash. `git log --oneline -5` is the source
of truth.

**The branch has never been pushed**, and is several commits ahead of `main`. That is why CI has
still never run a single check — see §0.

---

## 2. What exists and is verified

Verified means: exercised by a test that inspects database state after a real run, not merely that a
function exists.

**Phase 1 · Architecture** — complete. Spec, architecture, glossary, ADRs 0001–0016.

**Phase 2 · Database** — complete. 30 tables, 7 Alembic migrations, round-trip tested
(`test_alembic_migrations_roundtrip` applies head → base → head). Knowledge Objects are
row-per-version with a separate current pointer (ADR-0003). Claims are append-only: an immutable
identity row plus `claim_versions`, each version carrying the actor and the reason (ADR-0015).

**Phase 3 · Backend** — complete. FastAPI, Dramatiq worker, the 18-stage Run/Step state machine,
gates, approvals, resource locks, idempotency keys and the quota ledger. A Run traverses every stage
against fakes, suspends at each of the six manual/hybrid gates, and resumes.

**Phase 4 · Frontend + CLI** — CLI parity is real and tested. The dashboard exists
(`apps/web`) and builds, but no test drives it; treat its behaviour as unverified.

**Phase 5 · Agents** — complete. Topic discovery, research, extraction, verification, story angle,
script, storyboard, sound design and quality judge. An ORIGINS Topic yields a source-traced
Knowledge Object and a Script whose every beat cites verified claims.

**The pipeline reaches stage 18.** `test_full_18_stage_pipeline_traversal_with_human_gates` drives a
Run from creation to `completed` through all six human gates and then asserts, against the database:
every claim in the Knowledge Object resolves to evidence with a source and a snapshot; every beat
cites only claims from that Knowledge Object; exactly one `script_generation_v1` model call was
metered for the run; the storyboard references the persisted script and timing plan; render
artifacts exist for both aspect ratios with WebVTT captions carrying real cues; publication ran once
per artifact; and every `model_calls` row records `provider='fake'`, the adapter that actually ran.

### 2.1 Phase numbering — SPEC §15 is the numbering (D58, T-38)

This file used to number phases differently from `docs/SPEC.md` §15 and then declared the renumbered
phases complete. It now uses SPEC's numbering. The table maps the old STATUS names onto it so the
work is recounted rather than lost.

| SPEC §15 phase | What it means | Old STATUS name | State |
|---|---|---|---|
| 1 · Architecture | Spec, architecture, glossary, ADRs | Phase 1 (Architecture) | **complete** |
| 2 · Database | Schema, migrations, KO versioning, repositories | Phase 2 (Database & Persistence) | **complete** |
| 3 · Backend | FastAPI, worker, Run/Step state machine, gates, quota | Phase 3 (+ 3.1 remediation) | **complete** |
| 4 · Frontend + CLI | Dashboard shell, approval queue, CLI parity | Phase 4 (Frontend + Remotion Renderer) | **CLI complete; dashboard untested; the renderer half of the old name was never Phase 4 work** |
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
| 9 · AI imagery needs human approval | An `Approval` row on the asset-selection gate, resolved by step ID | `test_ai_generated_asset_cannot_be_used_without_approval` **and** `test_ai_generated_asset_is_usable_once_a_human_approves_the_gate` |
| 10 · Licenses enforced by a gate | `LicensePolicy.validate_asset_license` at asset discovery and storyboard cuts | `test_guard_6_policy_validation_methods_have_production_callers` |

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
- **Cassettes and the golden set.** Neither exists; `docs/ARCHITECTURE.md` §9 describes both.
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
- **Model IDs and the Ollama base URL are hardcoded.** ADR-0012 §3, §4; defects C-08, R-05.
- **Layering is enforced for `domain/` only.** `tests/unit/test_layering_boundaries.py` does not
  check the `adapters → application` direction. ADR-0014.
- **No repair attempt on malformed structured output.** `ARCHITECTURE.md` §5 promises one; both LLM
  adapters fail immediately instead.
- **Agents receive `topic_id` where a title belongs.** Four sites in `runner.py` pass
  `topic_title=run.topic_id`, so every prompt and search query sees `origin_of_mathematics` rather
  than the `topics` row's real title. Audit task **T-22** — the cheapest open item on the list.
- **`TimingPlan.total_duration_seconds` still defaults to `60.0`.** The pipeline's own plans are
  computed from beats, so the running system is honest, but any plan built without that field
  reports 60.0 and passes the 58–62 s deterministic check. Audit task **T-20**, defect R-04.
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

---

## 5. Where to look next

**Read order for the next session:** this file → `docs/AUDIT-2026-08-29.md` **§13** (what the
2026-08-31 verification found) and **§14** (the live task register, the ordered work list, the
start-up commands, and what not to do) → `docs/SPEC.md` §17 → `docs/ARCHITECTURE.md` §11 → the
relevant ADR → the code.

`docs/AUDIT-2026-08-29.md` is the authoritative register of what is broken. Its §14.2 gives the
open tasks in the order they should be worked and says why that order. The first two, in short:

1. **T-00 / T-11 — CI.** Cannot be closed by a session; the branch has never been pushed. Until it
   is, every number in §0 above is one machine's word.
2. **T-22 — load the real topic title.** Four lines, immediate quality effect.

**Do not start T-34** (the honest real-provider run) before **T-29** and **T-30**. The Gemini free
tier allows 20 requests a day and a correct run needs 6–9; that scarcity is the direct cause of the
2026-08-29 fabrication incident. Re-tiering onto Ollama first is what makes the attempt survivable.

### Session close-out checklist

Every working session ends by doing all of these. They exist because each was skipped at least once
and the result was a document that read as truth.

- [ ] Re-run `uv run ruff check .`, `uv run mypy .`, `uv run pytest`; paste the raw output into §0
      of this file. Never carry a number forward (**R7**).
- [ ] Update §1 with the real HEAD and whether the tree is clean.
- [ ] Move anything newly true into §2, anything newly known-absent into §3, anything deliberately
      left into §4 with the decision ID.
- [ ] Tick a task in the audit's §6 **only** if its own *Done when* is met; otherwise write which
      part is done under the task and leave the box open (**T-50**).
- [ ] Record every judgement call in `docs/DECISIONS.md` with the why, and file an ADR if it
      introduced a dependency, changed a data model, changed a layer boundary, added a provider
      category, or contradicted an existing ADR.
- [ ] Re-verify `docs/ARCHITECTURE.md` §11 and `docs/SPEC.md` §17 if the session touched structure
      or behaviour, and say which side of each row changed.
