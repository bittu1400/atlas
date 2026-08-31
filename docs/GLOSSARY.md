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

**Focus Snapshot** — Point-in-time capture of research criteria and scoping parameters frozen by value within a Run.

**Scope Mode** — `hard` (never leave the Focus), `soft` (prefer the Focus, allow adjacent graph nodes),
`exploratory` (Focus as a seed). Default is `soft`.

---

## Knowledge

**Topic** — A candidate subject for one output, with its own lifecycle: `proposed → approved →
researching → knowledge_ready → blocked | rejected | published`. An entity with state, not a string.

**Knowledge Object (KO)** — The canonical, versioned container of everything known about a Topic.
The single source every renderer reads from. Never edited in place.

**Knowledge Object Status** — Lifecycle states of a Knowledge Object version: `draft` | `verified` | `published` | `archived`.

**Claim** — One atomic statement, typed by **Assertion Type**, carrying confidence and a validity window.
Its identity is permanent; its state is append-only (see **Claim Version**).

**Claim Version** — One immutable revision of a Claim's state — text, assertion type, confidence,
status — together with the actor who wrote it and the reason they gave. A Claim's current state is
its highest-numbered version. Nothing is ever updated in place (Invariant 4, ADR-0015).

### Claim Status

The verification verdict assigned by the Pipeline:
*   **unverified**: Freshly extracted, not yet subjected to verification.
*   **verified**: The claim is factually accurate based on provided evidence.
*   **unsupported**: Evidence exists but does not adequately substantiate the claim, or no evidence exists.
*   **refuted**: Evidence contradicts the claim.
*   **contested**: The system could not reach a high-confidence consensus, escalating to the operator.

**Assertion Type** — `fact` | `inference` | `opinion` | `contested`. Required on every Claim. A Claim
whose type is `inference` must name the Claims it was inferred from.

**Evidence** — A specific passage in a specific Source that supports or contradicts a Claim, with a
locator (page, offset, quote) and a stance of `supports` or `contradicts`.

**Traceability Chain** — Complete 4-tuple provenance tree (`ClaimEvidenceLink`, `Evidence`, `Source`, `Snapshot`) proving physical chain of custody from statement to retrieved bytes.

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

**Story Angle** — The narrative framing chosen for one Script, selected at pipeline stage 8 from the
verified Claims of the Knowledge Object and stored on the Script. One Knowledge Object supports many
angles; `branch` rejection means "same knowledge, different angle".

**Caption Cue** — One `(start, end, text)` triple in a Timing Plan, exported as WebVTT. Cues are
computed from Beats, never authored separately, so captions cannot drift from the on-screen text.

**Sound Track** — The audio composition plan for one Storyboard: a music bed at a ducking level, an
ordered list of **SFX Cues**, and a loudness target. Aligned to the Timing Plan, like everything else.

**SFX Cue** — One sound effect placed at a timestamp with a volume and a cue type (`keystroke`,
`transition`, `ambient`).

**Storyboard** — The pairing of Beats to visual **Scenes**.

**Scene** — One visual unit: an Asset plus its motion treatment (pan, scale, grade) and duration.

**Asset** — A concrete media file with a resolved license: archival still, generated image, sound
effect, or music bed.

**Asset License** — The license record governing an Asset, including whether the intended use is
permitted, what attribution is required, and where that attribution must appear.

**Render Target** — The output configuration: aspect ratio, resolution, frame rate, duration. One
Storyboard renders to several Targets.

**Render Artifact** — A produced media file for one Render Target, persisted with the Storyboard it
came from, its captions, its duration, and the metadata recording how it was made.

**Production Artifact** — Collective name for the per-Run artifacts of pipeline stages 8-15: the
**Script**, its **Timing Plan**, the **Storyboard**, and the **Render Artifacts**. Each is persisted
and immutable: a rewrite is a new artifact with a new ID, never an edit (ADR-0016). Later stages read
the persisted artifact rather than regenerating one, so the artifact an operator approved is the
artifact that ships.

**Stub Adapter** — An adapter that stands in for a capability Atlas does not have yet, named `Stub*`
so it can never be mistaken for the real thing (rule R3). `StubRenderer`, `StubPublisher` and
`StubImageGenerator` are the current ones; `docs/STATUS.md` says what does not exist.

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

**Resource Lock** — Named concurrency lease with expiring TTL (e.g. GPU lease) to coordinate exclusive resource access across workers.

**Idempotency Key** — Unique composite execution key (`run_id:step_name:input_hash`) preventing duplicate side-effects.

**Step Output Reference** — The `steps.output_artifact_ref` value a Step writes when it succeeds: the
ID of the artifact it produced, or a short marker for stages that produce none. It is how a later
stage finds what an earlier one made, and it survives suspension and resumption because it is a
database column. Stages read it rather than regenerating (ADR-0016).

**Model Call** — One row in `model_calls`: the provider, model ID, prompt version, parameters, token
counts, latency and outcome of a single invocation. Its provider and model are taken from the
adapter that actually executed, never from the routing table, so provenance cannot disagree with
reality. Distinct from the **Quota Ledger**, which aggregates consumption per provider per window.

**Verbatim Evidence Check** — The rule, enforced in `ExtractionAgent`, that an Evidence quote is
persisted only if it occurs as a substring of the decoded Snapshot bytes (whitespace normalised).
A quote that fails is dropped and logged `evidence.rejected_not_verbatim`; the stage does not fail.
This is what makes a hallucinated quote unable to become Evidence.

**Pre-Output Invariant Gate** — The single backstop check run immediately before rendering, which
fails the Run if any Claim referenced by the Script is not `verified`, has no Evidence link, or has
no provenance row. It exists so that fabrication is structurally unable to reach an output, rather
than merely discouraged. Distinct from a **Gate**: no human resolves it and it never suspends — it
either passes or fails the Run with a typed domain exception.

**Plausible-History Guard** — Guard 7 in `tests/unit/test_no_fabrication.py`. It refuses any string
inside `adapters/fakes/`, and any claim-shaped fixture value anywhere in `tests/` or
`packages/atlas/src`, that carries the shape of a historical fact: a century reference, a dated
claim, a named polity, or the language of attestation. It exists because six guards existed on
2026-08-29 and none of them noticed two fabricated historical sentences being typed into a fake
(defect SC-01). A fixture must read as obviously synthetic — `SUBJECT_A`, `SOURCE_B` — so that a
fixture can never be mistaken for a fact.

**Claim-Shaped Fixture** — A test or source value passed as `text=`, `quote=`, `summary=`,
`snippet=` or `narrative_thesis=`, i.e. one that becomes the content of a Claim, an Evidence quote,
or a source snippet. The distinction matters because these are the only strings where an invented
sentence can be mistaken for knowledge; a century in a Focus facet or in an operator's critique is
ordinary text and is deliberately not guarded.

**Traceability Refusal** — The rule, `validate_knowledge_object_claims_are_traceable` in
`domain/knowledge/invariants.py`, that a Knowledge Object version naming a Claim with no
`claim_evidence` row is **refused** with a typed exception naming the offending Claim IDs — never
saved with the untraceable Claims filtered out. Enforced in `KnowledgeRepository.save_version`
before any row is written, so a refused version leaves no version row, no claim rows and no current
pointer. Silent filtering (defect SC-04) let an Invariant 1 violation pass as a green test.

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

**Provider** — An external capability behind an interface: `Llm`, `StructuredLlm`, `Embedder`,
`Search`, `SourceFetcher`, `ImageSearch`, `ImageGenerator`, `SoundLibrary`, `Renderer`, `Storage`,
`Publisher`, `Notifier`, `QueueBroker`, and `Speech` *(seam defined, unimplemented)*. All fourteen
live in `application/ports/`; `repositories.py` holds the persistence ports, which are not Providers.

**Queue Broker** — The port that enqueues a Run for background execution. Postgres is the queue
(ADR-0001); `DramatiqQueueBroker` is the production adapter.

**Adapter** — One concrete implementation of a Provider interface. The only place a vendor SDK appears.

**Tier** — Where work is allowed to run. **Tier 0** free deterministic sources, **Tier 1** local models
on the GPU, **Tier 2** hosted free-tier models. Routing policy assigns each task a Tier.

**Routing Policy** — Configuration mapping task kinds to a Tier, a model, and a fallback chain.

**Quota Ledger** — The append-only record of consumption per provider per window (minute and day),
with the Run that consumed it. The budget enforcer. Per-invocation detail lives in **Model Call**.

**Prompt Version** — The immutable identifier of a prompt template. Part of the cache key and of every
artifact's provenance.
