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
