# ADR-0004 — Provider ladder and quota governance

**Status:** Accepted
**Date:** 2026-07-30
**Relates to:** D2, D6, D20

## Context

Atlas must cost nothing to run, while producing three exceptional 60-second videos per day.

An early assumption needed correcting: a Gemini Advanced / Google One AI Premium subscription is a
consumer application subscription and grants no API access. There is no legitimate programmatic path to
it. The free path is **Google AI Studio**, a separate product that issues API keys with a free tier on
Flash-class models, rate-limited per minute and per day. Two properties of that tier matter
architecturally: on the free tier the provider may use submitted content to improve their products, and
free tiers change without notice.

Available hardware is one RTX 5070 Laptop GPU with 8 GB of VRAM — enough for an 8B-class quantized model
plus an embedding model resident together, but not enough to also host an image model concurrently.

The operator proposed a sensible-sounding policy: search free sources first, and only call a model when
something is not found there. That instinct is correct for *retrieval* and wrong for *transformation*,
and the distinction is the core of this decision.

## Decision

**A three-tier ladder, with routing by task kind, and quota treated as the scarce resource.**

| Tier | Runs on | Used for |
|---|---|---|
| **0** | Free deterministic APIs and archives — OpenAlex, Crossref, arXiv, Europe PMC, Semantic Scholar, Wikidata, Wikipedia, Wikimedia Commons, Internet Archive, government portals | Every fact, every source, every image |
| **1** | Local models on the GPU via Ollama — `qwen3:8b` quantized, `nomic-embed-text` | Embeddings, classification, deduplication, entity extraction, relevance filtering, first-pass summarization, drafts |
| **2** | Hosted free-tier frontier models — Gemini Flash via AI Studio | Claim extraction fidelity, Beat writing, quality judging, angle ranking |

**Retrieval never consumes Tier 2.** A fact absent from Tier 0 is not obtained by asking a model; the
Claim is marked `unsupported` and dropped. This is stricter than the proposed policy and deliberately so:
falling back to a model for missing facts would launder model recall into the provenance chain and quietly
void the central invariant. The "not found in free sources" condition triggers exactly one thing — AI
image generation at priority 4, with mandatory human approval.

**Transformation cannot be avoided by searching harder.** Extracting structured claims from a paper,
ranking story angles, and writing a line that lands over an archival photograph have no source to be
retrieved from. Those calls are reduced by *choosing the right tier*, not by searching more.

Supporting mechanisms:

- **Routing policy as configuration.** A YAML map from task kind to tier, model, parameters, and fallback
  chain. No agent names a model.
- **Capability negotiation.** Free-tier models differ in context window and structured-output support, so
  ports expose capabilities and the router checks them before dispatch.
- **Quota ledger.** Append-only, per provider, tracking both the minute and day windows, with persisted
  token buckets shared across workers. Every call is metered before it is issued.
  *(Implemented 2026-08-31, D115. Both halves of this bullet were false until then: `check_rate_limits`
  counted in process memory and never read the ledger, and two agents reached a provider with no
  QuotaManager at all. Audit §15, defects V-02 and V-04. Recorded here because an ADR whose mechanism
  was never built is indistinguishable from one that was, and this one read as done for three phases.)*
- **Per-Run reservations.** Each Run receives a share of the daily budget with a reserve pool for retries,
  so the first video of the day cannot starve the third.
- **Response caching** keyed on `hash(inputs) + prompt_version + model + parameters`. Retries and
  re-renders are free, and reproducibility comes for free with it.
- **Data policy.** Tier 2 receives public-knowledge research and script text only. Nothing operator-private
  is sent, which is what makes the free tier's training-use terms acceptable here.
- **Degradation.** If a task requires Tier 2 and quota is exhausted, the Run suspends and notifies. It does
  not silently fall back to a weaker model and publish worse work, because `prompt.md` puts craftsmanship
  above throughput.

## Alternatives considered

**Automating the Gemini web application.** Would use the existing subscription. Rejected outright: it
violates the provider's terms, breaks on any frontend change, and is not a foundation for a platform.

**Local models only.** Fully private, unlimited, no dependency on anyone's free tier. Rejected because an
8B model writing the on-screen Beats would be visibly weaker on the one artifact the viewer actually
reads. Tier 1 handles volume precisely so Tier 2 can be spent where quality is visible.

**Hosted models for everything.** Simplest routing and best per-call quality, but it exhausts a free tier
within one video and then costs money. It also wastes frontier capability on deduplication.

**The proposed two-tier policy — free sources, then model fallback for anything missing.** Rejected as
stated because it would let models supply facts. Adopted in the form that is actually correct: Tier 0 owns
all retrieval, Tier 1 absorbs transformation volume, Tier 2 is reserved for viewer-visible quality.

**Cost-based budgeting.** Meaningless at zero spend. Requests per day is the real constraint, so the
ledger meters requests and tokens against provider windows rather than dollars.

## Consequences

- Atlas runs at zero monetary cost with a stated, testable quota budget.
- Provider independence stops being a principle and becomes operational necessity: when a free tier
  changes, an adapter is swapped rather than production stopping.
- Caching plus Step idempotency means a crash costs no quota, which is what makes retries safe at all.
- GPU work must be serialized — Tier 1 inference, image generation, and Remotion rendering contend for the
  same 8 GB. Handled by the resource lease in ADR-0001.
- Every model call site must go through the metering path. An unmetered call is a defect, not an
  optimization.
- Free-tier limits must be verified against live provider documentation before the budget is fixed, and
  re-verified periodically.

## Trade-offs accepted

We depend on a free tier that can change or disappear, and we accept that the provider may use submitted
prompts to improve their products — acceptable only because the content is public-knowledge research about
subjects like chess and pizza. We accept that Tier 1 output is weaker than Tier 2 and that some quality is
lost on the tasks we route locally. We accept that rate limits make the pipeline latency-bound in ways a
paid tier would not be.

## Revisit when

- A paid budget becomes available; the routing policy is the only thing that needs to change.
- The free tier's terms or limits change materially.
- Judge calibration shows Tier 1 tasks measurably dragging quality scores down.
- Hardware changes — more VRAM would move image generation, and possibly script drafting, to Tier 1.
