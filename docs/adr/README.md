# Architecture Decision Records

An ADR records **why** a decision was made, what was rejected, and what it costs. It is written once and
never quietly edited. When a decision changes, write a new ADR that supersedes the old one and mark the
old one `Superseded by ADR-NNNN`.

## When an ADR is required

- Introducing, replacing, or removing a dependency
- Changing a data model in a way that requires a migration
- Changing the dependency direction between layers
- Adding a provider category
- Contradicting an existing ADR
- Any choice a competent engineer might reasonably reverse in six months

Not required for: implementation detail inside a module, refactoring that preserves interfaces, or
anything already settled in `docs/DECISIONS.md` without dispute.

## What an ADR may never do

**An ADR may not authorise breaking an invariant.** It records *how* Atlas does something; the
invariant list in `CLAUDE.md` bounds *what* Atlas may do at all. Any ADR that appears to widen those
bounds is void on its face and must be superseded, not followed — even if Accepted, even if old,
even if code already depends on it. See ADR-0011, which exists because ADR-0010 did exactly this.

**Every ADR must state which invariants it touches and confirm it weakens none.**

An ADR also does not exist until it has a file in this directory. ADR-0010 was written straight into
`docs/DECISIONS.md`, which is how it skipped review.

## Format

Copy `0000-template.md`. Number sequentially, never reuse a number. Status is one of `Proposed`,
`Accepted`, `Superseded`, `Rejected`. Every ADR must contain a **Trade-offs accepted** section and a
**Revisit when** section — a decision without a stated cost and a stated expiry condition is not a
decision, it is a preference.

## Index

| ADR | Title | Status |
|---|---|---|
| [0001](0001-orchestration-and-durability.md) | Orchestration and durability | Accepted |
| [0002](0002-focus-model.md) | The Focus model — scoping research by Field and Note | Accepted |
| [0003](0003-knowledge-versioning-and-storage.md) | Knowledge versioning and storage shape | Accepted |
| [0004](0004-provider-ladder-and-quota.md) | Provider ladder and quota governance | Accepted |
| [0005](0005-renderer-remotion.md) | Remotion as the primary renderer | Accepted |
| [0006](0006-timing-model.md) | The Timing Plan as canonical pacing artifact | Accepted |
| [0007](0007-publishing-schedule-and-time-zones.md) | Publishing schedule and time zones | Accepted |
| [0008](0008-p0-data-integrity-remediation.md) | P0 data-integrity remediation | Accepted |
| [0009](0009-phase-6-production-integration.md) | Phase 6 production integration and DI container | Accepted |
| — | ~~0010 — Phase 7 orchestrator verification bypass~~ | **VOID — never filed here; see `docs/DECISIONS.md` and ADR-0011** |
| [0011](0011-retraction-of-adr-0010.md) | Retraction of ADR-0010 — a bypass is not a decision | Accepted |
| [0012](0012-tier-1-primary-inference.md) | Tier 1 becomes primary inference; Tier 2 reserved for verification | Accepted |
| [0013](0013-fabricated-data-quarantine.md) | Fabricated data is quarantined, never deleted | Accepted |
| [0014](0014-anti-fabrication-enforcement.md) | Anti-fabrication rules enforced by CI and pre-commit | Accepted |
| [0015](0015-append-only-claim-versions.md) | Claim state is append-only: identity row plus `claim_versions` | Accepted |
| [0016](0016-production-artifacts-are-persisted.md) | Scripts, timing plans, storyboards and render artifacts are persisted | Accepted |
