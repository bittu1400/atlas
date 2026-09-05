# ADR-0018 — Operator interface browser testing with Playwright

**Status:** Accepted  
**Date:** 2026-09-03  
**Deciders:** operator  
**Extends:** ADR-0017  
**Relates to:** ADR-0014, ADR-0017, `CLAUDE.md` → R3, R4, R5, R8, R13, Invariants 1, 4  
**Introduces dependency:** `@playwright/test` (dev dependency in `apps/web`)  

## Context

ADR-0017 introduced Guard 8 to prevent the operator interface from becoming a fabrication surface. However, ADR-0017 accepted a clear trade-off:

> Guard 8 is coarser than Guard 7: it scans file text rather than parsing an AST... It also cannot see anything the browser composes. We accept that, because the incident it targets was blunt... and because the honest fix for the residue is a browser test, which is recorded as open rather than substituted for.

ADR-0017's *Revisit when* specifically stated:

> A browser test exists, at which point Guard 8's file-specific checks (rows 3 and 4) can be replaced by assertions about what the screen actually renders...

Task **T-55** recorded this as the single most valuable missing test in the project: Guard 8 proves the sources hold no fixture, but nothing proved that the browser actually renders what the API returns rather than a hardcoded literal or simulated decision.

## Decision

**The operator dashboard is verified in a real headless browser using Playwright against `apps/web` with route-level API enforcement, wired directly into root `pnpm test` and CI.**

### 1. Four Core Behavioral Assertions (Task T-55)

The test suite (`apps/web/e2e/dashboard.spec.ts`) directly verifies the four failure modes that enabled defect V-03:

1. **API Property Rendering:** A Run row renders the dynamic `topic_id` returned by the API, proving the table does not display hardcoded topics.
2. **Gate Identity Rendering:** A pending Gate renders its dynamic `step_id`, proving the operator is shown the true step under review.
3. **Failed Action Truthfulness:** When gate approval fails (HTTP 500 / error), the UI displays the error banner with failure details and keeps the gate pending, proving failed actions are never presented as successful decisions (Rules R5, R8).
4. **Provenance Hash Rendering:** The Knowledge panel renders the exact `snapshot_sha256` prefix returned by the API, proving provenance hashes originate from database rows rather than literals.

### 2. Negative Proof (Defect Sensitivity)

Per Task T-55's *Done when*, the test suite was verified to fail immediately if a component is changed to render a literal instead of its prop (verified against `RunsTable.tsx`).

### 3. CI and Local Monorepo Integration

- `pnpm --filter @atlas/web test` and root `pnpm test` run Playwright in headless Chromium.
- `.github/workflows/ci.yml` installs Playwright Chromium dependencies and runs `pnpm test` as a blocking gate before package builds.

## Invariants Touched

- **Invariant 1 (No fact without a source):** Strengthened. The operator screen is verified to render genuine API snapshot hashes.
- **Rules R4, R5, R8, R13:** Enforced. A failed gate action cannot falsely report success; dynamic props cannot be replaced by static fixtures without failing the suite.
- **Weakens none.**

## Alternatives Considered

- **Vitest + React Testing Library with JSDOM:** Rejected as primary browser test runner. JSDOM does not render layout, real browser events, or real browser network stacks. As ADR-0017 and T-55 noted, component tests in JSDOM prove less than real browser rendering.
- **Python-based `pytest-playwright`:** Rejected because front-end developers work within TypeScript tooling (`pnpm dev`, `vite`, `playwright`). Running Playwright via `pnpm test` maintains idiomatic TypeScript types for web testing while keeping CI execution clean.

## Trade-offs Accepted

- Adds `@playwright/test` to `apps/web/devDependencies` and requires downloading Chromium in CI (`pnpm exec playwright install --with-deps chromium`), adding ~15 seconds to CI execution.
- Headless test execution takes ~2.5 seconds locally.

## Revisit When

- The dashboard migrates to a full multi-page framework or server-side rendered architecture requiring different browser test harnesses.
