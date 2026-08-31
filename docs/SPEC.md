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

**Eighteen stages.** Gate policy shown is the Phase 1 default for ORIGINS and is the literal content
of `DEFAULT_STAGE_GATES` in `application/policies/gate_policy.py`; the order is the literal content of
`STAGE_SEQUENCE` in `application/pipeline/runner.py`. **Updated 2026-08-31 (T-39, D101):** this table
previously listed 17 stages and disagreed with the code, which splits "Script" into generation and
approval. The code's split is the better shape and is adopted here.

| # | `PipelineStage` | Produces | Gate | Suspends? |
|---|---|---|---|---|
| 1 | `IDEA_DISCOVERY` | Candidate Topics within Focus | automatic | no |
| 2 | `TOPIC_SELECTION` | An approved Topic | **manual** | always |
| 3 | `RESEARCH` | Sources + Snapshots (Tier 0 only, no model calls) | automatic | no |
| 4 | `CLAIM_EXTRACTION` | Claims (`unverified`) with verbatim Evidence, Knowledge Object v1 | automatic | no |
| 5 | `FACT_VERIFICATION` | Verification verdicts, contradictions surfaced | hybrid | only when a Claim is `contested` |
| 6 | `KNOWLEDGE_OBJECT` | A versioned KO the operator has seen | **manual** | always |
| 7 | `STORY_ANGLE` | Operator consent to proceed to scripting | hybrid | always |
| 8 | `SCRIPT_GENERATION` | The selected Story Angle, the Script, and its Timing Plan — **persisted** | automatic | no |
| 9 | `SCRIPT_APPROVAL` | Operator approval of that Script | **manual** | always |
| 10 | `TIMING_PLAN` | Validation and publication of the persisted Timing Plan's ID | automatic | no |
| 11 | `ASSET_DISCOVERY` | Candidate archival stills, license-resolved | automatic | no |
| 12 | `ASSET_SELECTION` | Chosen Assets | **manual** — always manual for AI-generated | always |
| 13 | `STORYBOARD_CUTS` | Beat-to-Scene pairing with motion treatment — **persisted** | automatic | no |
| 14 | `SOUND_DESIGN` | SFX and music layers aligned to the Timing Plan | automatic | no |
| 15 | `REMOTION_RENDER` | One Render Artifact per Render Target — **persisted** | automatic | no |
| 16 | `QUALITY_CHECK` | Quality Report | automatic, **hard gate** | no |
| 17 | `FINAL_APPROVAL` | Publishable artifact | **manual** | always |
| 18 | `PUBLISH` | External publication IDs | automatic | no |

**Where the Story Angle is actually chosen.** Stage 7 is a gate, and a suspending stage runs no
handler — so the operator's decision at stage 7 is "proceed to scripting", not "approve this angle".
The angle itself is selected at stage 8 by `ScriptAgent.select_story_angle` from the verified Claims,
and stored on the Script. Making stage 7 approve a *named* angle requires a change to gate mechanics
and is deliberately not done (**D92**). Recorded here so the table is not read as more than it is.

**Stage 15 is named `REMOTION_RENDER` while the renderer is a stub.** The stage name describes the
intended implementation and appears in `steps.step_name` rows already written, so renaming it is a
data migration for no behavioural gain. The *adapter* is honestly named `StubRenderer` (rule R3,
**D96**), and `docs/STATUS.md` §3 says rendering does not exist.

**Stage hand-off.** Every stage writes what it produced into `steps.output_artifact_ref`, and later
stages read it. No stage regenerates an artifact an earlier stage already made — that was defect
R-02 and is now structurally prevented by **ADR-0016**.

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

Verified against HEAD `9938244`. **Re-verified 2026-08-29 (Stage C remediation session, audit §11)**
against HEAD `c776b59` plus the working tree: **no row changed.** That session's work (T-43, T-44,
T-45, T-51, T-52) removed fabricated fixture text, added the anti-fabrication guard, and made
Knowledge Object assembly refuse untraceable Claims — all of which move the code **towards** §1–16,
not away from it, and none of which touches a divergence recorded here.

**Re-verified 2026-08-31** (independent verification session, audit §13), against commit `714cade`
and the documentation pass that followed it, on a clean tree. **§17.1 is closed** (T-39: §6 adopts the 18-stage split). **§17.2 is closed in
full.** **§17.3 and §17.4 are partially closed.** **§17.5's duration bound (R-04) is narrowed but
still open.** Each row below says which side changed.

### 17.1 Pipeline stage count and numbering (§6) — **CLOSED 2026-08-31 (T-39, D101)**

§6 listed 17 stages; `STAGE_SEQUENCE` has 18, splitting "Script" into `SCRIPT_GENERATION`
(automatic) and `SCRIPT_APPROVAL` (manual). **The doc changed:** §6 now transcribes
`STAGE_SEQUENCE` and `DEFAULT_STAGE_GATES` directly, eighteen rows, with the gate and the
suspend-or-not behaviour of each. `docs/STATUS.md` also says 18. All three agree.

### 17.2 Gate policy (§6)

**Updated 2026-08-29 (Stage C review, D71).** The stage 5 and stage 7 rows were **deleted**: after
T-37, `DEFAULT_STAGE_GATES` sets both to `HYBRID`, the runner passes `has_contested_claims` and
`has_ai_generated_assets`, and no branch in `gate_policy.py` is unreachable. Per **D55** a row is
deleted only when the code matches the doc.

**Updated 2026-08-31.** The stage 12 row is **closed**; the publish row is **partially closed** and
renumbered to 18 to match §6. The section is kept as the record of what was wrong and which side
moved.

| Spec stage | Spec gate | `DEFAULT_STAGE_GATES` in code | Divergence |
|---|---|---|---|
| 11 · Asset selection | **manual**, always manual for AI-generated | `MANUAL`, forced `MANUAL` when an AI asset is present | **Closed 2026-08-31 (defects SC-03, B1).** The check runs at `STORYBOARD_CUTS` and resolves the asset-selection gate by its deterministic step ID, then requires an `Approval` row with `decision == approved` — `ExecutionRepository.list_approvals_for_run` was added for it. A gate row flipped to `approved` with no Approval is not approval. Both directions are tested: an unapproved AI asset fails the run, an approved one renders. |
| 18 · Publish | "Phase 1: manual export. Interface stubbed." | `AUTOMATIC` | **Partially closed 2026-08-31 (defect R-03). Code changed:** the stage now loads the persisted Render Artifacts and calls `Publisher.publish` once per artifact, recording the returned IDs in `steps.output_artifact_ref`; with no publisher wired it raises `PublisherNotConfiguredError` rather than returning success. **Still open:** the publisher is `StubPublisher`, so a completed Run has published nothing real — it returns `stub:<artifact-id>` — and the stage does not consult `PublishScheduler` or the blackout rule. T-21's remaining bar is that a stub publisher must fail the stage loudly; see **D102** for why that was not done in the same change. |



### 17.3 Approval semantics (§7) — partially closed 2026-08-31

> "Approval records the actor, the timestamp, and the artifact version approved."

The `approvals` table records `actor_id` and `created_at`. It still records **no artifact version**,
and neither does `gates` (defect R-10, task **T-25**). **Open.**

**The second half of this row is closed. Code changed:** the script is no longer regenerated at five
stages (defect R-02, ADR-0016), so the artifact a human approved *is* the artifact that proceeds. It
is now derivable — a gate names a `step_id`, and the `SCRIPT_GENERATION` step for the same Run names
the Script ID — but derivable is not recorded, and a stale approval after a rework is still not
detectable. T-25 remains the fix.

### 17.4 Source policy (§9) and provider ladder (§11)

- §11 / ADR-0004: "Retrieval never consumes Tier 2. A fact absent from Tier 0 is not obtained by
  asking a model." Honoured in the routing table. **Violated in practice on 2026-08-29** by the
  hardcoded-payload incident, where facts came from neither Tier 0 nor a model.
- ~~The production container wires `FakeSearch` and `FakeSourceFetcher` for Tier 0 retrieval
  (defect C-01). Real `WikipediaSearch` and `HttpSourceFetcher` exist and are unwired (C-02).~~
  **Closed 2026-08-31 (D97). Code changed:** the container wires `WikipediaSearch` and
  `HttpSourceFetcher`, and imports nothing from `adapters/fakes/`. **Caveat, stated plainly:** the
  wiring is verified by a guard test, not by a network run. No Run has yet fetched a real URL, so
  T-26's "a snapshot whose bytes came off the network" is **not** demonstrated — that is **T-34**.
- Tier assignments in §11 are amended by **ADR-0012** (Tier 1 becomes primary; Tier 2 reserved for
  fact verification) after measurement showed the Gemini free tier allows 20 requests/day.
- §11 / ADR-0004: "Every call is metered before it is issued", over "persisted token buckets shared
  across workers". **Both halves were false until 2026-08-31 (defects V-02, V-04). Code changed:**
  stage 1's topic-discovery call and stage 13's two embedding calls had no `QuotaManager` at all,
  and `check_rate_limits` counted in process memory while never reading the `quota_ledger` rows it
  wrote — so every CLI invocation and every worker process began with a full daily budget. Both
  agents now meter, and the windows are computed from the ledger (**D109**, **D110**, **D115**).

### 17.5 Quality (§8)

- §8.3 deterministic checks: **narrowed 2026-08-31, still open (defect R-04, task T-20).** The
  pipeline's own plans are now honest — `ScriptAgent._compute_timing_plan` sets
  `total_duration_seconds` from the summed beat durations, and the persisted plan is what the judge
  reads (ADR-0016), so a pipeline-produced plan can no longer lie. **What remains:**
  `TimingPlan.total_duration_seconds` still carries `default=60.0` in
  `domain/script/models.py`, so any plan constructed without that field — a fixture, a future
  caller, a repair path — reports 60.0 regardless of its beats and passes the 58–62 s check. The
  default must go and the value must be derived or validated at construction.
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

**Done 2026-08-31 (T-38, T-31).** `docs/STATUS.md` was rewritten from measurement and uses this
section's numbering; its §2.1 carries the mapping table. The 2026-08-29 STATUS body is archived
unchanged at `docs/archive/STATUS-2026-08-29.md` under rule R11. The table above stays as the record
of the confusion, with one correction: SPEC's Phase 5 row said "two agents violate the invariants
they enforce (D-02, D-04)" — both are closed (T-13, T-14), and the pipeline now runs all 18 stages
against fakes. SPEC's Phase 6 and Phase 7 remain unbuilt.

**Also decided (D57):** the real Remotion renderer is **deferred**. Phase 7 ends at a correct
Knowledge Object, a verified Script and a real Storyboard. `RemotionRenderer` was renamed
`StubRenderer` on 2026-08-31 (D96), and the data path into it is now fixed: the renderer receives
the persisted Storyboard and Timing Plan for the run (ADR-0016), so the real renderer is a drop-in.

### 17.7 Open questions (§16) — status at 2026-08-29

| Question | Change |
|---|---|
| ORIGINS audience region | Still open. Needed before Publishing. |
| Retention policy | Still open, and now also governs quarantine schemas (**ADR-0013**). |
| Novelty threshold | Still open, and cannot be approached: novelty detection does not exist (§17.6). |
| Quality threshold of 78 | Still open. Now blocking: **ADR-0012** requires the golden set to measure the Tier 1 quality drop. |
| Backup and restore | Partially answered — `atlas backup` / `atlas restore` wrap `pg_dump` and `tar`. Untested against a real restore, and must now decide whether quarantine schemas travel with a backup (**ADR-0013**). |

### 17.8 Divergences found on 2026-08-31

New rows, opened by the verification session (audit §13). None is a correction to §1–16.

| Spec section | Divergence | Task |
|---|---|---|
| §6 | Agents are called with `topic_title=run.topic_id` at four sites in `runner.py`. The `topics` row holds the real title and it is never read, so every prompt and search query sees an ID where a title belongs (defects R-06, R-07). | **T-22** |
| §6 | The gate-stage branch of `PipelineRunner._dispatch_stage_handler` — the one returning `gate_passed_<stage>` for the six manual/hybrid stages — is **unreachable**. Those stages always suspend, and `_execute_stage` returns before dispatch in every path that follows. Harmless as a defensive fallback, but it is dead code that reads like behaviour. | **new, T-53** |
| §7 | `PUBLISH` returns success while `StubPublisher` is wired. A Run can reach `completed` having published nothing. Stated in `docs/STATUS.md` §3, but it is the exact shape of "it ran is not it worked" (**R6**). | **T-21** |
| §11 | `ImageCandidate` list at stage 13 is re-searched rather than loaded from stage 11, so the candidate set the operator approved at the stage 12 gate is not provably the set the Storyboard drew from. The Storyboard itself is persisted, so everything from stage 13 onward is stable. | **new, T-54** (ADR-0016 trade-offs) |

### 17.9 Divergences found by the second verification on 2026-08-31

Opened and, except where noted, closed by the session recorded in audit §15. Listed because §17 is
the register of where the spec and the code disagreed, not only of where they still do.

| Spec section | Divergence | State |
|---|---|---|
| §10.1 / Invariant 10 | The license gate compared one dialect against its allowlist while the two image adapters emit the other two, so every validly licensed CC asset was rejected and only "Public domain" survived — enforcement that over-blocks silently is as untrustworthy as enforcement that under-blocks. The blocked-term test was a substring match, so the "nc" inside "licence" read as non-commercial. | **Closed** (D112, V-10) |
| §11 / Invariant 8 | Two model call sites were unmetered and the quota ledger was never read back. | **Closed** (D109, D110, D115, V-02, V-04) |
| §7 | The operator screen reported a **failed** gate approval as a recorded decision, and displayed invented claims, snapshot hashes, telemetry and quota figures. §7's human gate is only as real as what the human is shown. | **Closed** (D111–D114, V-03) |
| §12 | The dashboard's wire types described an API that does not exist — `current_stage`, `gate.stage`, `gate.metadata`, a `'open'` gate status, a `/gates` route, a `POST /runs` body with no `topic_id` — so it had never once rendered live data. | **Closed** (D111, V-03) |
| §8.4 | Still open: no golden set, and now also **no browser test**. Guard 8 asserts the dashboard's *sources* carry no fixture; nothing asserts what the screen renders. | **Open**, `docs/STATUS.md` §3 |
