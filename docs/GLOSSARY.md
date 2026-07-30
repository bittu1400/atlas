# Glossary — Atlas Ubiquitous Language

One name per concept. If code and this file disagree, this file wins and the code is a defect.
Adding a concept means adding it here **first**.

---

## Focus & scoping

**Field** *(UI label only)* — The category the operator selects, e.g. `Animal`, `History`, `Technology`.
Internally always called a **Domain**, because "field" already means a database column and a form input.
Never use `field` as an identifier for this concept.

**Domain** — A named area of knowledge that carries a **Research Profile**. Data, not an enum.

**Research Profile** — The policy attached to a Domain: preferred source APIs, source allowlists and
tiers, query-expansion vocabulary, and disambiguation hints. This is what makes a Domain more than a tag.

**Note** *(UI label only)* — The free-text subject the operator types, e.g. `tiger`. Internally the
**Subject**, which resolves to an **Entity**.

**Entity** — A canonical, externally-identified thing (Wikidata QID). `tiger` the animal is `Q19939`,
distinct from the golfer and the operating system. Anchoring to an Entity, not a string, is what makes
deduplication and graph traversal reliable.

**Facet** — One typed `(dimension, value)` constraint inside a Focus. Domain and Subject are the first
two facets; era, region, and audience are future facets. The UI shows two inputs; the model holds a list.

**Focus** — A named, versioned set of Facets plus a **Scope Mode**. Created once, captured by value into
every Run that uses it, never mutated afterwards.

**Active Focus** — A pointer naming the Focus that supplies the default for *newly created* Runs. It is
a default, not global state: changing it never affects a Run already in flight.

**Scope Mode** — `hard` (never leave the Focus), `soft` (prefer the Focus, allow adjacent graph nodes),
`exploratory` (Focus as a seed). Default is `soft`.

---

## Knowledge

**Topic** — A candidate subject for one output, with its own lifecycle: `proposed → approved →
researching → knowledge_ready → blocked | rejected | published`. An entity with state, not a string.

**Knowledge Object (KO)** — The canonical, versioned container of everything known about a Topic.
The single source every renderer reads from. Never edited in place.

**Claim** — One atomic statement, typed by **Assertion Type**, carrying confidence and a validity window.

**Assertion Type** — `fact` | `inference` | `opinion` | `contested`. Required on every Claim. A Claim
whose type is `inference` must name the Claims it was inferred from.

**Evidence** — A specific passage in a specific Source that supports or contradicts a Claim, with a
locator (page, offset, quote) and a stance of `supports` or `contradicts`.

**Source** — A retrievable document: paper, archive record, government publication, book, official doc.
Carries a **Source Tier**.

**Source Tier** — `primary` | `peer_reviewed` | `institutional` | `reference` | `unvetted`. Wikipedia is
`reference` — usable for verification and navigation, never as sole support for a Claim.

**Snapshot** — The archived bytes of a retrieved Source, with content hash and retrieval timestamp.
Citations point at Snapshots, so they survive link rot.

**Impact Index** — The reverse map from a Claim to every published artifact that used it. What makes
retraction and correction possible.

---

## Rendering

**Channel** — A publishing identity: `ORIGINS`, `WHY`, `HUMANS`. Carries a **Style Profile**.

**Style Profile** — A Channel's craft rules as data: typography, palette, motion language, pacing
constants, line-length limits, hook patterns, sound signature, target duration, imagery preferences.
The main defence against three channels sounding like one model.

**Script** — The ordered sequence of **Beats** for one output. Not prose. Versioned.

**Beat** — One unit of on-screen text: its lines, emphasis, reveal style, dwell hint, and the Claim IDs
that license it. The atom of the no-narration format.

**Timing Plan** — The computed schedule that fits Beats to the target duration: reveal rate, hold
duration, cut points, beat-to-music alignment. The single artifact that text animation, sound effects,
cuts, and captions all read from, guaranteeing they cannot drift apart.

**Storyboard** — The pairing of Beats to visual **Scenes**.

**Scene** — One visual unit: an Asset plus its motion treatment (pan, scale, grade) and duration.

**Asset** — A concrete media file with a resolved license: archival still, generated image, sound
effect, or music bed.

**Asset License** — The license record governing an Asset, including whether the intended use is
permitted, what attribution is required, and where that attribution must appear.

**Render Target** — The output configuration: aspect ratio, resolution, frame rate, duration. One
Storyboard renders to several Targets.

**Render** — A produced media file for one Render Target, recording every input version that made it.

---

## Execution

**Run** — One execution of the pipeline for one Topic under one captured Focus. The unit of tracing,
quota accounting, and resumption.

**Step** — One stage within a Run, individually retryable, idempotent, and checkpointed.

**Gate** — A point where a Run may suspend: `automatic`, `manual`, or `hybrid`. A Gate is a database
row, not a framework feature.

**Approval** — A human decision on a Gate, recording actor, timestamp, and — on rejection — structured
feedback that regeneration consumes.

**Rejection Feedback** — Typed, targeted criticism (which Beat, which dimension, what is wrong). Plain
"rejected" is not accepted by the system; feedback is what makes the next attempt better.

**Quality Report** — Scores per rubric dimension plus the deterministic check results, with a pass or
fail verdict against the Channel's threshold.

**Novelty Check** — Similarity comparison of a Script against the published corpus, preventing Atlas
from repeating its own hooks and phrasings.

---

## Scheduling

**Operator Timezone** — `Asia/Kathmandu`. Governs dashboard display, approval reminders, and notification
quiet hours. **Never** used to compute publish times.

**Audience Timezone** — A property of a Channel, naming the region its viewers live in. The only clock
used to compute publish slots. Different Channels may differ.

**Provider Reset Timezone** — The boundary on which a provider's free-tier daily quota resets. A property
of the provider, not of Atlas, and distinct from both clocks above.

**Publishing Window** — A seeded or learned recommendation of `(platform, format, day_of_week, local_start,
local_end)` with a rank, a source, and a confidence. Expressed in audience-local time, always.

**Blackout Window** — The enforced prohibition on publishing before 06:00 or after 22:00 audience-local.
A constraint the scheduler cannot violate, not a warning.

**Publish Slot** — A concrete UTC instant produced by resolving a Publishing Window against a Channel's
Audience Timezone and applying blackout rules.

**Scheduling Strategy** — `audience_local` (default) or `global_utc_peak`. Separate code paths; neither is
a conversion of the other.

---

## Providers

**Provider** — An external capability behind an interface: `Llm`, `Embedder`, `Search`, `SourceFetcher`,
`ImageGenerator`, `ImageSearch`, `Renderer`, `Storage`, `Publisher`, `Notifier`, `Speech` *(seam defined,
unimplemented)*.

**Adapter** — One concrete implementation of a Provider interface. The only place a vendor SDK appears.

**Tier** — Where work is allowed to run. **Tier 0** free deterministic sources, **Tier 1** local models
on the GPU, **Tier 2** hosted free-tier models. Routing policy assigns each task a Tier.

**Routing Policy** — Configuration mapping task kinds to a Tier, a model, and a fallback chain.

**Quota Ledger** — The append-only record of every model call: provider, model, tokens, latency, cost,
outcome. Both the budget enforcer and the source of the Agent Monitor's data.

**Prompt Version** — The immutable identifier of a prompt template. Part of the cache key and of every
artifact's provenance.
