# ADR-0007 — Publishing schedule and time zones

**Status:** Accepted
**Date:** 2026-07-30
**Relates to:** D37, D38, ADR-0001, ADR-0004
**Implementation:** schema seam in Phase 2, scheduler in Phase 8

## Context

Atlas targets three published artifacts per day, and publishing timing measurably affects reach. Research
supplied by the operator establishes the governing facts:

- Every credible "best time to post" study measures engagement in the **audience's own local time**. A
  recommendation of "Tue 11am" means 11am wherever the viewer is. It is not a UTC instant.
- Optimal windows differ by platform *and* by content format, and platforms split into weekday-favored
  (LinkedIn, X, Discord, Snapchat) and weekend-favored (TikTok, Pinterest, Tumblr, Kwai) groups. No single
  day-of-week rule applies across platforms.
- A hard floor and ceiling exist: nothing before ~06:00 or after ~22:00 audience-local performs well, on
  any platform, with no found exceptions.
- A separate global UTC traffic curve peaks at ~10:00, ~14:00, and ~21:00 UTC, with 21:00 the tallest.
  This applies only to worldwide simultaneous drops, not to single-audience scheduling.

The operator's own timezone is `Asia/Kathmandu` (UTC+05:45, no DST).

The trap this ADR exists to prevent: treating the operator's timezone as the publishing clock. Atlas
produces English-language content whose audience is overwhelmingly not in Nepal. Publishing at 10:00
Kathmandu is 04:15 UTC — which is 00:15 US Eastern and 05:15 London, violating the hard floor for the two
largest English-language audiences while feeling like a perfectly reasonable working hour locally.
Conversely, 14:00 UTC serves both well and falls at 19:45 Kathmandu, a workable approval hour.

The tallest global peak, 21:00 UTC, is 02:45 Kathmandu the following day. It cannot be hit manually.

## Decision

**Four distinct clocks, never conflated. Publishing windows are seeded data, not code. Blackout rules are
enforced constraints.**

### 1. Four clocks

| Clock | Value | Governs |
|---|---|---|
| **UTC** | — | Every stored timestamp, without exception |
| **Operator** | `Asia/Kathmandu` | Dashboard display, approval reminders, notification quiet hours |
| **Audience** | per Channel | The *only* clock that computes publish slots |
| **Provider reset** | per provider | Quota ledger day boundaries — free tiers reset on the provider's boundary, not ours |

`audience_timezone` is a property of the Channel, because different channels may target different regions.
It is never a global setting and never inherited from the operator.

### 2. Windows as data

A `publishing_windows` table holds `(platform, format, day_of_week, local_start, local_end, rank, source,
confidence)`, seeded from the supplied research. Values are **priors**, carrying a confidence level and a
source attribution, designed to be superseded by Atlas's own analytics in Phase 9 without a migration.

Format is part of the key, not an afterthought: the research itself distinguishes YouTube long-form
(Sunday strongest) from general uploads, and short vertical content behaves differently again.

### 3. Blackouts are enforced, not advisory

No slot may fall before 06:00 or after 22:00 audience-local. This is a constraint the scheduler cannot
violate — the same enforcement posture Atlas applies to license compatibility. Violation is a defect, not
a warning.

### 4. Weekday/weekend split is a platform property

Each platform carries a day-of-week preference profile. The schema makes it impossible to express a single
universal posting day across platforms, because the research is explicit that no such day exists.

### 5. Two strategies, never one converted into the other

- **`audience_local`** (default) — resolve the Channel's audience timezone, select the highest-ranked
  window for the platform and format, apply blackouts, emit a UTC instant.
- **`global_utc_peak`** — for worldwide simultaneous drops, target the 10:00 / 14:00 / 21:00 UTC peaks
  directly.

These are separate code paths. Converting an audience-local recommendation into UTC and treating it as a
global peak, or vice versa, is precisely the error the research warns against.

### 6. Slot allocation

Three artifacts per day are assigned to distinct ranked windows with a minimum spacing constraint, never
two in the same window. Allocation is deterministic domain logic — pure, unit-testable, property-tested
over calendars and timezones, and involving no model call. Scheduling is arithmetic, not inference.

### 7. Time arithmetic uses the tz database

Slots are computed with IANA zone rules at scheduling time. A stored UTC offset is never used for future
scheduling. Kathmandu has no DST; the audiences do. A cached `-0400` breaks in October.

## Alternatives considered

**Operator timezone as the publishing clock.** The literal reading of "go with my local time." Rejected on
the operator's own hard rule: it places every publication outside the acceptable window for the primary
audience. The operator timezone is retained for its correct purpose — display and reminders.

**Hardcoded best-time constants.** Fast to write. Rejected because these are third-party aggregate
benchmarks about other people's audiences, and the entire point of Phase 9 is to replace them with
measured reality. Constants in code cannot carry confidence, provenance, or be learned over.

**A single global UTC schedule for everything.** Simple and would appear to satisfy the traffic-curve
data. Rejected because it conflates the two datasets — the UTC curve describes aggregate global traffic,
not when a specific audience is receptive, and applying it to a single-region audience produces exactly
the 00:15-US-Eastern failure above.

**Letting a model choose publish times.** Rejected for the same reasons as ADR-0006's timing decision:
non-deterministic, spends quota on arithmetic, and cannot guarantee a hard constraint like the blackout
window.

## Consequences

- Publishing timing is correct for the audience rather than convenient for the operator.
- The seeded research is auditable — every window records where it came from and how much to trust it.
- Phase 9 analytics can override priors per channel and per platform with no schema change.
- The Channel entity gains `audience_timezone`, and `publishing_windows` plus `blackout_rules` land in the
  **Phase 2** schema, so Phase 8 wires a scheduler to existing tables rather than retrofitting a data model.
- The tallest global peak being 02:45 local is a concrete argument for automated scheduled publishing.
  Phase 1 remains manual upload; this is a reason not to stay there.
- Notification quiet hours use the operator clock, so approval reminders never fire at 03:00 Kathmandu.

## Trade-offs accepted

We are seeding the system with benchmarks measured on other people's audiences and other content formats,
and some of them will prove wrong for ORIGINS. We accept that because a wrong prior with recorded
confidence is strictly better than no policy, and the structure makes correction cheap.

We also accept that at 60 seconds vertical, publish timing is a **weak lever**. Short vertical content is
distributed algorithmically with a long tail rather than by subscription notification, and the cited
studies largely measure general and long-form content — the research's own note that Sunday suits YouTube
long-form *specifically* concedes the format split. The machinery is built because it is cheap and becomes
genuinely valuable if durations extend, not because it will decide whether these videos succeed. Per-video
quality and consistency dominate at this length, and no scheduling policy substitutes for either.

## Revisit when

- Atlas has 90 days of its own performance data, at which point priors should be measurably replaced.
- Durations extend to long-form, where timing becomes a materially stronger lever.
- A second Channel targets a different audience region, exercising the per-Channel clock for real.
- A platform is added whose day-of-week profile is not yet represented.
