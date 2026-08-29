# Atlas — Product Specification

**Status:** Phase 1, architecture settled · **Date:** 2026-07-30 · **Supersedes:** nothing
**Source of vision:** `prompt.md` (immutable) · **Rationale:** `docs/adr/`

This document defines *what Atlas does* and *what correct means*. `docs/ARCHITECTURE.md` defines how it
is built. Where behaviour and code disagree, this document is right and the code is a defect.

> **2026-08-29 —** That last sentence has never been checked. See **§17** for every place the code
> currently disagrees with this spec, and `docs/AUDIT-2026-08-29.md` for why the check was overdue.
> This document is unchanged; §17 records the defects, it does not amend the spec.

---

## 1. Thesis

Atlas turns primary sources into a canonical, versioned **Knowledge Object**, then renders that
knowledge into publishable artifacts. Videos are the first renderer, not the product.

The discipline that makes this valuable is narrow and absolute: **every statement Atlas publishes can be
traced to evidence, and Atlas never invents a fact.** A language model in this system extracts,
structures, ranks, phrases, and judges. It never supplies knowledge.

Everything else — the pipeline, the dashboard, the renderer — is machinery in service of that.

---

## 2. Phase 1 scope

**In:** the ORIGINS channel · one Topic to one approved Render, end to end · 60-second default duration ·
9:16 and 16:9 outputs · on-screen text with sound design, no narration · public-domain archival imagery ·
zero monetary cost · human approval at every gate that matters · full CLI parity with the dashboard.

**Out, with the seam built and documented:** narration and speech · automated YouTube publishing · the
WHY and HUMANS channels · semantic search over the knowledge graph (bypass mode is the default) ·
long-form durations · multi-language · analytics feedback loop.

**Explicitly not built:** multi-user roles, Kubernetes, Temporal, distributed workers.

---

## 3. Invariants

These hold at every stage. A pipeline that violates one halts rather than degrades.

1. Every on-screen assertion resolves to Claim IDs → Evidence IDs → Source → Snapshot.
2. No Claim is created from model recall. A Claim without Evidence is `unsupported` and is dropped.
3. Every Claim carries an assertion type: `fact`, `inference`, `opinion`, or `contested`.
4. Conflicting evidence is stored in full. Atlas presents disagreement; it does not resolve it.
5. Knowledge is append-only. Every revision is preserved with actor, timestamp, and reason.
6. Every asset's license permits the intended use, verified by a gate before render.
7. AI-generated imagery requires explicit human approval, always.
8. Every model call is metered against the quota ledger before it is issued.
9. Every artifact records provider, model, prompt version, parameters, and input versions.
10. A Run's configuration is captured at creation and never re-read from mutable settings.

---

## 4. Output format

### 4.1 The format, stated plainly

A 60-second silent-friendly video. On-screen kinetic text carries the story. Public-domain archival
imagery sits behind it with slow motion treatment. Cuts land on the music beat. Sound design —
keystroke texture, transitions, an ambient bed — supplies the physicality a voice would normally give.
It reads correctly with the sound off, which is how most of it will first be seen.

### 4.2 Budgets at 60 seconds

Derived from silent reading comprehension (~2.0–2.5 effective words/second once dwell time is included),
not from speech pacing. These are Style Profile constants, not hard-coded numbers.

| Property | Budget |
|---|---|
| Total on-screen words | 110–150 |
| Beats | 12–18 |
| Seconds per beat | 3.0–4.5 |
| Words per beat | 6–12 |
| Lines per beat | 1–2 |
| Characters per line | ≤ 28 (legibility floor is set by 9:16) |
| Distinct images | 6–12 |
| Music beds | 1 |
| Transition effects | 3–6 |

Duration is an operator input, default `60`. Every budget above scales from it; nothing assumes 60.

### 4.3 Render targets

Both are produced from one Storyboard. Layout is responsive from the first component — text safe areas,
type scale, and image crop focal points are computed per target, never hardcoded.

| Target | Aspect | Resolution | Purpose |
|---|---|---|---|
| `vertical` | 9:16 | 1080×1920 | Shorts, Reels, TikTok — primary discovery surface at this length |
| `horizontal` | 16:9 | 1920×1080 | Traditional YouTube, and the path to long-form later |

Frame rate 30. Loudness normalized to −14 LUFS (±1). Captions exported as WebVTT, generated directly
from the Timing Plan — frame-accurate by construction, never transcribed.

### 4.4 Typography and sound

Libre-licensed, embeddable fonts only. Each Channel's Style Profile fixes a display face and a body
face; ORIGINS pairs a high-contrast display serif with Inter for supporting text, appropriate to
archival material.

Sound sources: Freesound CC0 subset and Pixabay, with per-sample license provenance tracked exactly as
images are. Keystroke texture is sample-based with randomized velocity and timbre variation — a fixed
sample repeated on every reveal sounds mechanical and will fail the quality gate.

---

## 5. Focus — the operator's control surface

Two inputs, as specified: a **Field** selector and a **Note** text box. Underneath, both are Facets of a
`Focus` object, so adding era, region, or audience later is configuration rather than redesign. See
**ADR-0002**.

- **Field** selects a **Domain**, which carries a **Research Profile** — the source allowlist, preferred
  APIs, and vocabulary for that area. `Animal` reaches for zoology and conservation databases; `History`
  reaches for archives and primary documents. The Field is a policy selector, not a tag.
- **Note** resolves to a canonical **Entity** (Wikidata QID) at Focus creation. The Field disambiguates
  the Note: `Animal` + `tiger` is `Q19939`, not the golfer, not the tank, not the OS release. Ambiguity
  is presented to the operator for confirmation, never guessed silently.
- **Scope Mode** defaults to `soft`: prefer the Focus, allow adjacent knowledge-graph nodes. `hard`
  never leaves the Focus and will starve research on most topics. `exploratory` treats it as a seed.
- **Active Focus** supplies the default for newly created Runs. Runs already in flight keep the Focus
  they captured. Changing the Active Focus is never retroactive.

Precedence: explicit Run arguments → Active Focus → Channel default.

Failure mode that must be handled, not hidden: a Focus too narrow to yield candidate Topics returns
`no_candidates_in_scope` with a suggestion to widen the Scope Mode. Silence is not acceptable here.

---

## 6. Pipeline

Gate policy shown is the Phase 1 default for ORIGINS. Every gate is switchable to `automatic`,
`manual`, or `hybrid` from the dashboard and the CLI.

| # | Stage | Produces | Gate |
|---|---|---|---|
| 1 | Idea Discovery | Candidate Topics within Focus | automatic |
| 2 | Topic selection | An approved Topic | **manual** |
| 3 | Research | Sources + Snapshots (Tier 0 only, no model calls) | automatic |
| 4 | Claim extraction | Claims with Evidence locators | automatic |
| 5 | Fact verification | Verification verdicts, contradictions surfaced | hybrid — manual on `contested` |
| 6 | Knowledge Object | A versioned KO | **manual** |
| 7 | Story angle | Ranked angles, one selected | hybrid — Atlas proposes, operator picks |
| 8 | Script | Beats, each carrying Claim IDs | **manual** |
| 9 | Timing Plan | Fitted schedule for the target duration | automatic |
| 10 | Asset discovery | Candidate archival stills, license-resolved | automatic |
| 11 | Asset selection | Chosen Assets | **manual** — always manual for AI-generated |
| 12 | Storyboard | Beat-to-Scene pairing with motion treatment | automatic |
| 13 | Sound design | SFX and music layers aligned to the Timing Plan | automatic |
| 14 | Render | One Render per Render Target | automatic |
| 15 | Quality check | Quality Report | automatic, **hard gate** |
| 16 | Final approval | Publishable artifact | **manual** |
| 17 | Publish | *Phase 1: manual export. Interface stubbed.* | — |

A Run suspended at a gate persists indefinitely and resumes exactly where it stopped. Suspension is a
row in a table, not a held process.

---

## 7. Approval and rejection

Approval records the actor, the timestamp, and the artifact version approved. Immutable.

**Rejection must carry structured feedback** — which Beat or Asset, which rubric dimension, and what is
wrong. Free-text-only rejection is rejected by the API. This is deliberate: the feedback is fed back
into regeneration as typed input, which makes attempt two meaningfully better than attempt one. A
rejection that teaches nothing is a wasted quota cycle.

Rejection routes to one of: `regenerate` with feedback attached, `branch` to try a different angle from
the same Knowledge Object, or `abandon` with a recorded reason. Rejection reasons are analyzed over time
— they are the highest-signal quality data Atlas will ever have.

---

## 8. Quality — the definition of good

`prompt.md` demands craftsmanship over quantity. That is only enforceable if "good" is measurable, so it
is defined here. See **D18/D19**.

### 8.1 Rubric

Scored 0–100 per dimension. Judge-scored dimensions use a rubric prompt with a frontier free-tier model;
deterministic dimensions are computed.

| Dimension | Weight | Method |
|---|---|---|
| Sourcing integrity | 20 | deterministic + judge |
| Hook strength (first 3 seconds) | 15 | judge |
| Narrative arc and payoff | 15 | judge |
| Language craft — absence of generic AI phrasing | 15 | judge + phrase blocklist |
| Factual density — insight per second | 10 | judge |
| Novelty against the published corpus | 10 | deterministic (embedding + n-gram) |
| Visual coherence and image relevance | 10 | judge |
| Technical compliance | 5 | deterministic |

### 8.2 Passing

A Render passes when **all** hold:

- Weighted total ≥ **78**
- No single dimension below **60**
- Every deterministic check passes

### 8.3 Deterministic checks — binary, non-negotiable

Every Beat carries at least one Claim ID · every referenced Claim has Evidence · every Asset is
license-cleared for the intended use · required attribution is present in both the end card and the
description · duration within ±2s of target · loudness −14 LUFS ±1 · all text inside safe margins in
*both* aspect ratios · captions exported and aligned · corpus similarity below the novelty threshold.

### 8.4 Calibration

The judge is calibrated against roughly 20 artifacts scored by hand before its scores are trusted as a
gate. Until calibration exists, the gate runs in advisory mode and says so. The golden set is versioned
and re-run on every prompt change — this is the regression suite for quality, and without it quality
drifts invisibly the first time a model or prompt changes.

---

## 9. Source policy

Preferred, in order: primary documents and archives · peer-reviewed literature (OpenAlex, Crossref,
arXiv, Europe PMC, Semantic Scholar) · government and institutional publications · books in the public
domain · official documentation. Wikipedia and Wikidata are `reference` tier: used for navigation,
disambiguation, and verification — never as sole support for a Claim.

SEO content farms and undated, unattributed web pages are excluded by allowlist, not by heuristic.

**Every retrieved Source is snapshotted** — bytes stored, content hashed, retrieval timestamped.
Citations resolve to the Snapshot. Link rot is a certainty, not a risk.

Fetching is polite by construction: `robots.txt` respected, per-domain rate limits, identifying
user-agent, conditional requests, and a cache that makes a re-run cost nothing.

---

## 10. Asset and license policy

Priority, per `prompt.md`: **1** Wikimedia Commons · **2** other public-domain archives (Smithsonian
Open Access, Library of Congress, NASA, Met Museum, Rijksmuseum, Openverse) · **3** operator-supplied
assets · **4** AI generation, locally, always human-approved.

If an Asset is rejected, Atlas searches for alternatives before escalating to the next priority tier.

### 10.1 License compatibility

Enforced by a gate before render. *This is an engineering policy encoding a conservative reading of
common licenses; it is not legal advice.*

| License | Verdict | Requirement |
|---|---|---|
| Public Domain / PD-Mark / CC0 | allowed | provenance recorded |
| CC BY | allowed | attribution in end card **and** description |
| CC BY-SA | allowed, flagged for review | attribution + share-alike implications noted |
| CC BY-NC, CC BY-NC-SA | **blocked** | non-commercial conflicts with monetization intent |
| CC BY-ND, CC BY-NC-ND | **blocked** | motion treatment and cropping are derivative works |
| Pexels / Pixabay / Unsplash terms | allowed with conditions | no attribution required, still recorded; blocked where identifiable people or trademarks appear |
| Freesound CC0 | allowed | provenance recorded |
| Freesound CC BY | allowed | attribution required |
| Unknown or ambiguous | **blocked** | unresolvable license is a blocker, never a warning |

Attribution is rendered into the video end card *and* the description text. A Render missing required
attribution fails the deterministic check.

### 10.2 Disclosure and content guardrails

- **Synthetic content disclosure.** Any Render containing AI-generated imagery is flagged in its
  publishing metadata so the platform's synthetic-content disclosure is set at upload. Recorded per
  Render, derived from Asset provenance rather than from operator memory.
- **No advice.** Atlas states what sources say about human behaviour; it never issues medical,
  psychological, financial, or legal advice or instruction. Enforced as a judge-scored check at the
  quality gate, and relevant primarily to the HUMANS channel, which is deferred.
- **Living persons.** Claims about identifiable living people require `primary` or `peer_reviewed` tier
  support. Reputational assertions from `reference` or `unvetted` tiers are dropped, not softened.

---

## 11. Provider ladder and quota

Atlas costs nothing to run. The scarce resource is **requests per day**, not dollars. See **ADR-0004**.

| Tier | What runs here | Cost | Used for |
|---|---|---|---|
| **0** | Free deterministic APIs and archives | none | all facts, all sources, all imagery |
| **1** | Local models on the 8GB GPU | none | embeddings, classification, dedup, entity extraction, relevance filtering, first-pass summarization, drafts |
| **2** | Hosted free-tier frontier models | none, rate-limited | claim extraction fidelity, Beat writing, quality judging, angle ranking |

**Retrieval never consumes Tier 2.** A fact absent from Tier 0 is not obtained by asking a model — it is
marked unsupported. The "not found in free sources" condition triggers exactly one thing: AI image
generation, at priority 4, with human approval.

Estimated per 60-second video: ~15–30 Tier-2 calls, ~50–150 Tier-1 calls. At three videos daily that is
roughly 45–90 Tier-2 calls per day, comfortably inside current free-tier limits — to be verified against
live provider documentation before the quota budget is fixed.

Two mechanisms matter more than any routing rule: **response caching** keyed on input hash plus prompt
version plus model, so retries and re-renders are free and reproducible; and **per-Run quota
reservations**, so the first video of the day cannot starve the third.

---

## 12. Failure semantics

Every failure has a defined, visible outcome. Nothing degrades silently.

| Situation | Behaviour |
|---|---|
| No candidate Topics in Focus | `no_candidates_in_scope`, suggest widening Scope Mode |
| Claim has no supporting Evidence | Claim marked `unsupported`, excluded from Script, retained in the KO |
| Sources contradict | both stored, Claim typed `contested`, manual gate raised |
| No license-clear image for a Scene | search alternatives → adjacent Entity imagery → procedural background → **block with a named reason**. Never a silent placeholder |
| Tier 2 quota exhausted | fall back down the chain; if the task requires Tier 2, suspend the Run and notify rather than degrade quality |
| Render fails mid-way | Step retried from its checkpoint; upstream Steps are never re-run |
| Quality gate fails | route to rework queue with per-dimension scores; never publish |
| Provider returns malformed output | schema validation, one repair attempt, then fail the Step loudly |

---

## 13. Non-functional targets

| Target | Value |
|---|---|
| Throughput | 3 approved Renders per day |
| Monetary cost | $0.00 |
| Human time per video | ≤ 10 minutes across all gates |
| Pipeline latency, topic to render | ≤ 90 minutes wall clock, excluding human wait |
| Render time per target | ≤ 5 minutes for 60 seconds |
| Full e2e test suite against fakes | ≤ 60 seconds, $0, no network |
| Storage growth | ≤ 500 MB per video including snapshots and both renders |

At three per day, roughly 1,100 videos and ~550 GB per year. Retention and archival policy is required
before month six.

---

## 14. Publishing schedule and time zones

Full rationale in **ADR-0007**. Scheduler is Phase 8; the schema seam lands in Phase 2.

### 14.1 Four clocks

Conflating any two is a defect.

| Clock | Value | Governs |
|---|---|---|
| **UTC** | — | Every stored timestamp, without exception |
| **Operator** | `Asia/Kathmandu` (UTC+05:45, no DST) | Dashboard display, approval reminders, notification quiet hours |
| **Audience** | per Channel | The only clock that computes publish slots |
| **Provider reset** | per provider | Quota ledger day boundaries — free tiers reset on the provider's boundary |

The operator clock is never the publishing clock. Atlas publishes English-language content whose audience
is not in Nepal: 10:00 Kathmandu is 00:15 US Eastern and 05:15 London, breaking the blackout floor for both
primary audiences. 14:00 UTC serves both and falls at 19:45 operator-local.

### 14.2 Windows

`publishing_windows` holds `(platform, format, day_of_week, local_start, local_end, rank, source,
confidence)`, seeded from external research as **priors** with recorded provenance, to be superseded by
Atlas's own analytics in Phase 9 without a migration. Format is part of the key — long-form and short
vertical behave differently.

Seeded values, audience-local: YouTube long-form Sunday, and Thursday ~09:00 · TikTok Tue–Thu 09:00–12:00
and 14:00–17:00, Saturday strongest · Instagram Tue–Thu 11:00–13:00, avoid Sunday daytime · LinkedIn
Mon–Wed 08:00–10:00 · Facebook Thu–Fri 13:00–15:00 · fallback where audience or platform is unknown, and
the current low-confidence seed for short vertical, Tue–Thu 09:00–11:00.

### 14.3 Enforced constraints

- **Blackout:** no slot before 06:00 or after 22:00 audience-local. Enforced, not advisory — the same
  posture as license compatibility.
- **Day-of-week profile is a platform property.** Weekday-favored and weekend-favored platforms are a real
  split; the schema cannot express a single universal posting day.
- **Slot allocation:** three artifacts per day occupy distinct ranked windows with minimum spacing.
  Deterministic domain logic, no model call.
- **Time arithmetic uses the IANA tz database at scheduling time.** Never a stored UTC offset — audiences
  observe DST even though the operator does not.

### 14.4 Strategies

`audience_local` (default) resolves the Channel's audience clock and emits a UTC instant.
`global_utc_peak` targets the ~10:00 / ~14:00 / ~21:00 UTC global peaks for worldwide simultaneous drops,
21:00 being the tallest. These are separate paths; neither is a conversion of the other.

Note that 21:00 UTC is 02:45 operator-local, unreachable manually — an argument for automated scheduling
rather than a reason to change Phase 1's manual upload.

### 14.5 Expected impact, stated honestly

At 60 seconds vertical, publish timing is a **weak lever**. Short vertical content is distributed
algorithmically with a long tail rather than by subscription notification, and the seeded research largely
measures general and long-form content. The machinery is built because it is cheap and becomes valuable if
durations extend. Per-video quality and consistency dominate at this length.

---

## 15. Phase plan

Each phase ends with acceptance criteria that are demonstrable, not asserted.

| Phase | Deliverable | Done when |
|---|---|---|
| **1 · Architecture** | This spec, ARCHITECTURE, glossary, ADRs 0001–0007 | Decisions recorded with rationale and trade-offs — **complete** |
| **2 · Database** | Schema, Alembic migrations, KO versioning, repositories, publishing-window tables | A KO can be written, revised, and read back at any prior version — **next** |
| **3 · Backend** | FastAPI, worker, Run/Step state machine, gates, quota ledger | A Run traverses every stage with fake providers, suspends at a gate, and resumes |
| **4 · Frontend + CLI** | Dashboard shell, approval queue, CLI parity | Every gate is approvable from both the browser and the terminal |
| **5 · Agents** | Research, extraction, verification, script, judge | An ORIGINS Topic yields a source-traced Knowledge Object and a Script |
| **6 · Knowledge system** | Graph, Focus, Entity binding, novelty, impact index | Focus constrains a real Run; corpus repetition is detected |
| **7 · Rendering** | Remotion compositions, Timing Plan, sound design, both targets | A 60-second video exists in both aspect ratios and passes every deterministic check |
| **8 · Publishing** | Publisher adapters, slot scheduler (§14), attribution rendering | Deferred until requested |
| **9 · Analytics** | Performance ingest, feedback contract | Deferred |
| **10 · Optimization** | Quota efficiency, caching, render speed | Deferred |

---

## 16. Open questions

Non-blocking, needed before the phase noted.

- **ORIGINS audience region** — sets the Channel's audience timezone. US-anchored is the largest English
  long-tail market; India is operationally closest to the operator; UK/Europe sits between. Required
  before Phase 8, and it is a per-Channel property so channels may differ.
- **Retention policy** for snapshots and superseded renders — required by month six.
- **Novelty threshold** — cannot be set until a corpus exists; provisional value in Phase 6.
- **Quality threshold of 78** — provisional, to be re-fixed after judge calibration.
- **Backup and restore** — Postgres PITR plus a portable export bundle; required before the first
  published video, since knowledge is the product and it is irreplaceable.

---

## 17. Implementation divergence register

**Added 2026-08-29.** Sections 1–16 are unchanged and remain product truth. This section records
where the code on disk disagrees with them. Per the header rule, **every row below is a defect in
the code, not a correction to the spec.** Defect IDs refer to `docs/AUDIT-2026-08-29.md` §3.

Verified against HEAD `9938244`.

### 17.1 Pipeline stage count and numbering (§6)

§6 lists **17** stages. `STAGE_SEQUENCE` in `application/pipeline/runner.py` has **18**: the code
splits spec stage 8 ("Script", manual) into two — `SCRIPT_GENERATION` (automatic) and
`SCRIPT_APPROVAL` (manual). That split is reasonable and the spec should probably adopt it, but
until it does, the two documents disagree and a third (`docs/phase-7-execution.md`, now retracted)
said 17 while `docs/STATUS.md` said 18.

**Action:** decide whether §6 adopts the 18-stage split, then make all three agree.

### 17.2 Gate policy (§6)

| Spec stage | Spec gate | `DEFAULT_STAGE_GATES` in code | Divergence |
|---|---|---|---|
| 5 · Fact verification | **hybrid** — manual on `contested` | `AUTOMATIC` | Contested claims are **never escalated to a human.** `GatePolicy.should_suspend` has the hybrid branch, but the runner calls it as `should_suspend(stage)` (`runner.py:268`), so `has_contested_claims` is always `False` and the branch is dead. |
| 7 · Story angle | **hybrid** — Atlas proposes, operator picks | `AUTOMATIC` | The operator never picks. The runner hardcodes `story_angle="Origins and Preservation"` (defect R-05). |
| 11 · Asset selection | **manual**, always manual for AI-generated | `MANUAL` | Suspends correctly, but the AI-specific branch is dead for the same reason: `has_ai_generated_assets` is never passed. Combined with `validate_ai_image_approval()` having no production caller (defect D-05), **Invariant 9 has no runtime enforcement at all.** |
| 17 · Publish | "Phase 1: manual export. Interface stubbed." | `AUTOMATIC` | The stage returns a string and never calls the publisher (defect R-03). "Stubbed" is accurate; "records that it did not publish" is not implemented. |

§6 also states "Every gate is switchable to `automatic`, `manual`, or `hybrid` from the dashboard and
the CLI." `GatePolicy.should_suspend` accepts a `policy_override` parameter; **no caller passes it**,
and no dashboard or CLI surface exists for it.

### 17.3 Approval semantics (§7)

> "Approval records the actor, the timestamp, and the artifact version approved."

The `approvals` table records `actor_id` and `created_at`. It records **no artifact version**, and
neither does `gates` (defect R-10). An approval therefore cannot identify what was approved — and
because the script is regenerated at five separate stages (defect R-02), the artifact a human
approved is provably not the artifact that proceeds.

### 17.4 Source policy (§9) and provider ladder (§11)

- §11 / ADR-0004: "Retrieval never consumes Tier 2. A fact absent from Tier 0 is not obtained by
  asking a model." Honoured in the routing table. **Violated in practice on 2026-08-29** by the
  hardcoded-payload incident, where facts came from neither Tier 0 nor a model.
- The production container wires `FakeSearch` and `FakeSourceFetcher` for Tier 0 retrieval
  (defect C-01). Real `WikipediaSearch` and `HttpSourceFetcher` exist and are unwired (C-02).
- Tier assignments in §11 are amended by **ADR-0012** (Tier 1 becomes primary; Tier 2 reserved for
  fact verification) after measurement showed the Gemini free tier allows 20 requests/day.

### 17.5 Quality (§8)

- §8.3 deterministic checks: the duration bound (58–62 s) is satisfied trivially because
  `TimingPlan.total_duration_seconds` **defaults to `60.0`** and is never computed from beats
  (defect R-04, `domain/script/models.py:90`). A plan holding 3.5 seconds of beats reports 60.0 and
  passes.
- §8.1 rubric: eight dimensions, implemented and enforced by Pydantic. Correct.
- §8.4 calibration and the golden set do not exist. This blocks ADR-0012's quality measurement.

### 17.6 Phase numbering (§15) — the documents use different phase numbers

This is the most confusing divergence in the repository and must be resolved before the next
session plans anything.

| Phase | §15 of this spec | `docs/STATUS.md` claims | Built? |
|---|---|---|---|
| 4 | Frontend + CLI | Frontend + Remotion Renderer | Frontend yes; renderer is an ffmpeg blue rectangle (C-03) |
| 5 | Agents | Agents & Intelligence Engine | Agents exist; two violate the invariants they enforce (D-02, D-04) |
| 6 | **Knowledge system** — graph, Focus, Entity binding, novelty, impact index | **Production Pipeline Integration** — a different deliverable entirely | Spec's Phase 6 was **never built**: no graph, no novelty policy, no impact index in `application/policies/` |
| 7 | **Rendering** — Remotion compositions, sound design, both targets | **End-to-End Execution** | Spec's Phase 7 was never built; STATUS's Phase 7 was fabricated (ADR-0011) |
| 8 | Publishing | — | Not built |

`docs/STATUS.md` silently renumbered the phases and then declared the renumbered ones complete. The
spec's Phase 6 (knowledge system: novelty detection, entity binding, claim impact index, graph) has
**no implementation at all** — `application/policies/` contains only `gate_policy.py`,
`license_policy.py` and `quota_policy.py`.

**Decided 2026-08-29 (D58):** adopt **this spec's** numbering, and add a table to `docs/STATUS.md`
mapping the old STATUS phase names onto these phases so the Phase-6 adapter work is recounted rather
than lost. Audit tasks **T-38** (reconcile) then **T-31** (rewrite STATUS), in that order.

**Also decided (D57):** the real Remotion renderer is **deferred**. Phase 7 ends at a correct
Knowledge Object, a verified Script and a real Storyboard. `RemotionRenderer` is renamed
`StubRenderer`; the data path into it is still fixed so the real renderer is a later drop-in.

### 17.7 Open questions (§16) — status at 2026-08-29

| Question | Change |
|---|---|
| ORIGINS audience region | Still open. Needed before Publishing. |
| Retention policy | Still open, and now also governs quarantine schemas (**ADR-0013**). |
| Novelty threshold | Still open, and cannot be approached: novelty detection does not exist (§17.6). |
| Quality threshold of 78 | Still open. Now blocking: **ADR-0012** requires the golden set to measure the Tier 1 quality drop. |
| Backup and restore | Partially answered — `atlas backup` / `atlas restore` wrap `pg_dump` and `tar`. Untested against a real restore, and must now decide whether quarantine schemas travel with a backup (**ADR-0013**). |
