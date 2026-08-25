# Atlas — Independent Repo Review (check-only, 2026-08-24)

Scope: full read of docs, Python backend (`packages/atlas`, `apps/api`, `apps/worker`,
`apps/cli`), TypeScript frontend (`apps/web`, `apps/renderer`, `packages/tokens`), tests,
and git history. Nothing was modified; all checks were run read-only.

---

## Verification results (ran myself)

| Check | Result |
|---|---|
| `uv run ruff check .` | Pass, 0 violations |
| `uv run mypy .` (strict) | Pass, 0 errors across 112 files |
| `uv run pytest -q` | Pass — 83/83 against live local PostgreSQL |
| `pnpm build` (web) | Pass; 577 kB JS chunk (no code splitting) |
| `pnpm --filter @atlas/renderer build` | Pass (tsc only) |
| `.env` tracked in git? | No — properly ignored |
| Provider SDKs outside adapters | None found |
| Naive `datetime.now()` in source | None found |
| f-string log messages | None found |
| `any` / `@ts-ignore` / non-null assertions in TS | None found |

The hygiene claims in STATUS.md are **true**. That is genuinely rare and worth saying.

---

## What is actually good

1. **Documentation discipline is exceptional.** STATUS/SPEC/ADR/GLOSSARY/DECISIONS split,
   "decided vs done" separation, ADRs with costs and reopen conditions. Most senior engineers
   don't do this.
2. **Invariants are enforced structurally**, not by convention: DB-level state transition
   validation, single-resolution gates, Invariant-9 approval enforcement
   (`AiImageUnapprovedError`), immutability triggers from migration `0002`.
3. **Layering holds.** Domain imports only pydantic; no SQLAlchemy/FastAPI/Dramatiq leakage;
   no provider SDKs outside adapter directories.
4. **Tests are fast, deterministic at the unit layer, and behaviour-named.** Unit tests
   (41) touch no DB; integration runs against `atlas_test` Postgres.
5. **Secrets hygiene** is clean: no `.env` in history, `.gitignore` covers media/models.

---

## Findings

### F1 — The dashboard can silently lie to the operator (highest severity)
`apps/web/src/api/client.ts:36` and `:100`: on any fetch failure, `getRuns` and `getGates`
fall back to **hardcoded mock data** ("run-8323-001", a fake Rosetta Stone gate). For a tool
whose purpose is operator review of publishable knowledge, a downed backend rendering
plausible-looking fake runs/gates is worse than an error screen — it trains the operator to
approve things that don't exist. Mock fallbacks belong behind an explicit dev flag
(`import.meta.env.DEV && MOCK_API`), never as silent catch blocks.

### F2 — Production DI wires fakes everywhere (scope honesty gap)
`apps/api/dependencies.py:101-111`: every provider port (LLM, search, fetcher, image gen,
publisher…) resolves to a `Fake*`. This is *correct* pre-Phase-5, but README says
"Phase 3 backend & state machine is 100% complete" without mentioning that the served
pipeline is entirely fake-backed. STATUS.md should state this plainly in §1, not leave it
to be discovered in code.

### F3 — No CI at all
No `.github/workflows/`. CLAUDE.md's own hard requirement — "the full pipeline must run
end-to-end in CI in seconds, for zero cost" — is unmet. All green checks currently depend
on one machine having Postgres running locally (`tests/conftest.py:16` defaults to
`localhost:5432`; there is no skip/failure mode when it's absent).

### F4 — `PipelineRunner` violates the repo's own size rules
`packages/atlas/src/atlas/application/pipeline/runner.py` is **727 lines**. CLAUDE.md caps
files at ~400 and functions at ~50. It passed lint/mypy but violates the stated working
agreement — either the cap or the file should give.

### F5 — Hardcoded dev API key in frontend source
`apps/web/src/api/client.ts:9`: `'atlas-dev-key'` committed in source. Combined with
`verify_api_key` skipping auth when `api_auth_enabled=false` (config default), auth is
effectively decorative today. Fine for now; must be env-driven before anything public-facing.

### F6 — SSE endpoint is a stub wearing production clothes
`apps/api/routes/events.py`: emits two canned events then closes; also has no
`verify_api_key` dependency (every other route has one). The dashboard's "live telemetry"
is cosmetic. Acceptable scaffolding, but it should be labelled as such in STATUS.

### F7 — Doc drift and copy-paste rot
- `README.md:14` claims "**68 tests**"; actual count is **83** (STATUS is right, README stale).
- `docs/STATUS.md:117` session log ends with garbled duplicated text:
  `"…Ready for Phase 5. |source files. Ready for Phase 4. |"`.

### F8 — Minor / observations
- Web bundle is 577 kB minified with a build warning; Remotion Player likely belongs in a
  lazy chunk.
- Renderer `sampleData.ts` ships sample beats with claim IDs (`CLM-001`…) pointing at no
  real knowledge object — harmless now, but ensure sample data can never reach a render
  output path once Phase 7 lands.
- Single-maintainer bus factor; docs mitigate this well.
- Git remote path (`.../bittusah/Projects/Personal/Intern/atlas.git`) suggests a
  subdirectory-style remote URL; verify it resolves as intended (STATUS already flags
  confirming repo visibility).

---

## Verdict

This is a **discipline-forward, honestly-documented codebase with unusually strong
foundations**: clean layering, structural invariant enforcement, strict types, fast tests,
and documentation quality that most teams never reach. The risks are not in craftsmanship
but in **claim-vs-reality gaps**: the dashboard mocks (F1), the unstated fake-provider
reality of the "complete" backend (F2), and the absent CI contradicting the project's own
written definition of done (F3).

Priority order if I were you: **F1 → F3 → F7 → F2 (doc note) → F4 → F5/F6 before Phase 5.**

Nothing was changed during this review; this file is the only artifact written.
