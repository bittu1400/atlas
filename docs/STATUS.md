# Status

**Last updated:** 2026-08-31 (independent verification session)
**HEAD:** `714cade` — see §1.

This file separates **decided** from **done**. Everything else in `docs/` records what Atlas *will*
be; this records where it actually stands. It is rewritten from measurement at the end of every
working session, and **every number in it comes from a command run in the session that wrote it**
(rule R7). The previous body is archived unchanged at
[`docs/archive/STATUS-2026-08-29.md`](archive/STATUS-2026-08-29.md); nothing in that file is a
current claim.

---

## 0. Measured baseline

Measured on 2026-08-31, in the session that wrote this section, on the tree that became commit
`714cade`.

```
$ uv run ruff check .
All checks passed!

$ uv run mypy .
Success: no issues found in 158 source files

$ uv run pytest --tb=no
122 passed in 13.31s
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

HEAD is `714cade` on branch `docs/audit-2026-08-29`; the working tree is clean. That commit carries
the 2026-08-29 Stage C work — which had never been committed, despite audit §12.3 claiming it was —
together with this session's remediation. The false claim is recorded as finding **A1** in audit
§13. The branch is **three commits ahead of `main` and has never been pushed**, which is why CI has
still never run.

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

**The pipeline reaches stage 18.** `test_full_17_stage_pipeline_traversal_with_human_gates` drives a
Run from creation to `completed` through all six human gates and then asserts, against the database:
every claim in the Knowledge Object resolves to evidence with a source and a snapshot; every beat
cites only claims from that Knowledge Object; exactly one `script_generation_v1` model call was
metered for the run; the storyboard references the persisted script and timing plan; render
artifacts exist for both aspect ratios with WebVTT captions carrying real cues; publication ran once
per artifact; and every `model_calls` row records `provider='fake'`, the adapter that actually ran.

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

---

## 5. Where to look next

`docs/AUDIT-2026-08-29.md` is the authoritative register of what is broken. Its §13 records the
2026-08-31 verification session: findings **A1–A2** (false status claims in §12) and **B1–B9** (real
defects the previous session did not find), and what was done about each.

Remaining audit tasks, in order: **T-00 / T-11** (CI — needs an operator push), **T-32** (the mypy
debt, now cleared but the task also asks for the strictness settings to be documented), **T-38**
(phase renumbering — this file now follows SPEC §15), and Stage E (replace the stubs named in §3
with real adapters).
