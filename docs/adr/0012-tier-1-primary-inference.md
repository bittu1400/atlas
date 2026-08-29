# ADR-0012 — Tier 1 (Ollama) becomes the primary inference tier; Tier 2 is reserved for verification

**Status:** Accepted
**Date:** 2026-08-29
**Deciders:** operator
**Relates to:** ADR-0004 (provider ladder and quota governance — amended, not superseded), D2, D6, D20, Invariant 8
**Amends:** ADR-0004 § routing policy. The three-tier ladder stands; the task-to-tier assignment changes.

## Context

ADR-0004 assigned five task kinds to Tier 2 (hosted Gemini Flash): claim extraction, verification,
story-angle ranking, script writing, and quality judging. That assignment was made on the assumption
of a workable free-tier budget.

Measured on 2026-08-29 against the live key:

- `gemini-2.0-flash`, the model ID hardcoded in `RoutingPolicy.DEFAULT_ROUTES`, is **retired**. The
  API returns `404: "This model models/gemini-2.0-flash is no longer available."`
- `gemini-3.6-flash`, its replacement, has a free-tier limit of **20 requests per day**
  (`generate_content_free_tier_requests`, limit 20). Not 1,500, which is what
  `GeminiLlm.capabilities` declares.
- A single correct pipeline run needs roughly 6–9 Tier 2 calls. The current runner needs far more,
  because it regenerates the script five separate times (defect R-02).

So the practical ceiling is two to three runs per day on a good day, and zero once a debugging
session has spent the budget — which is exactly the pressure that produced the ADR-0010 incident.
Tier 2 scarcity is not an operational inconvenience; it is the direct cause of the worst failure
this project has had.

Meanwhile Tier 1 is idle. An RTX 5070 Laptop with 8 GB VRAM hosts `qwen3:8b` quantized alongside
`nomic-embed-text`, which is what ADR-0004 provisioned it for. It has no request limit.

## Decision

**Tier 1 (`OllamaLlm`, `qwen3:8b`) becomes the default provider for every transformation task.
Tier 2 (Gemini Flash) is reserved for fact verification, and for nothing else by default.**

| Task kind | Tier before | Tier now |
|---|---|---|
| Entity extraction | 1 | 1 |
| Claim extraction | 2 | **1** |
| **Fact verification** | 2 | **2 — unchanged, this is the reserved use** |
| Story angle generation | 2 | **1** |
| Script writing | 2 | **1** |
| Quality judging | 2 | **1** |
| Retrieval, timing | 0 | 0 |

Verification keeps Tier 2 because it is the one task where a weaker model's error becomes a false
claim in the knowledge graph rather than a weaker sentence. Everything else degrades in quality;
verification degrades in *truth*, and truth is the product.

Supporting requirements, all of which are prerequisites and not follow-ups:

1. **`GeminiLlm.capabilities` must state the real limits** (20 rpd for `gemini-3.6-flash`) so
   `QuotaManager` refuses the 21st call locally, before the API does. Invariant 8 is met in form
   today and defeated in substance by a fabricated `rpd_limit=1500`.
2. **The container must wire a Tier 2 → Tier 1 fallback with backoff.** On 429 or 5xx, retry with
   backoff, then fall back to Ollama, and record the fallback in provenance so the artifact names
   the model that actually produced it.
3. **Model IDs move to `platform/config.py`.** No model ID may be a default argument in an adapter
   or a literal in a policy. The `gemini-2.0-flash` 404 survived because it was hardcoded in two
   places that disagreed with each other.
4. **Ollama's base URL moves to settings.** It is hardcoded to `http://localhost:11434` in
   `container.py:41` today, and Ollama was not running during the audit that found this.

## Alternatives considered

- **Accept 2–3 runs/day on Tier 2.** Lost. It leaves the exact scarcity that caused ADR-0010 in
  place, and it makes iteration on prompts — the thing that actually improves output quality —
  economically impossible.
- **Buy a paid Gemini key.** Lost on the founding constraint: `prompt.md` and ADR-0004 commit Atlas
  to free tiers, and Invariant 8 treats quota as a first-class resource precisely because of that.
  Revisit if quality measurement (below) shows Tier 1 cannot carry script writing.
- **Move everything to Tier 1 including verification.** Lost. A local 8B model judging whether a
  quote supports a claim is the weakest possible link in the traceability chain, and Invariant 1
  makes that link load-bearing. Verification is worth the whole daily budget.
- **Route by task quality requirement at runtime.** Lost as speculative generality — one route table
  is enough until measurement shows it is not (`CLAUDE.md` → no speculative generality).

## Consequences

- Pipeline runs become effectively unlimited, and prompt iteration becomes cheap. This removes the
  standing incentive that produced the fabrication.
- Output quality on script writing and angle ranking will drop. That is expected and must be
  **measured, not assumed**: the golden quality set (ARCHITECTURE §9, not yet built) becomes a
  prerequisite for judging whether the drop is acceptable.
- Ollama becomes a hard runtime dependency for a run to start. The container must fail loudly at
  construction if it is unreachable, not partway through stage 4.
- The GPU semaphore (ADR-0001) now serialises more work: `qwen3:8b` holds the GPU for most stages,
  and local Stable Diffusion and Remotion's Chromium must queue behind it. Expect longer wall-clock
  runs on one 8 GB card.
- `RoutingPolicy.DEFAULT_ROUTES` must be rewritten, and its `use_fakes=True` default removed
  (defect D-01) in the same change, or provenance will keep recording `provider='fake'` regardless
  of which tier actually ran.

## Trade-offs accepted

We are trading output quality for iteration volume and for the removal of a failure incentive.
Sixty-second scripts written by an 8B local model will be worse than Gemini's until the prompts are
tuned, and we are choosing to find that out with real measurements rather than to protect a number
we cannot afford to produce. We also accept a heavier local machine: every run now occupies the GPU.

## Revisit when

- The golden quality set shows Tier 1 script writing scoring below the 78 threshold consistently
  after prompt tuning — then either promote script writing back to Tier 2 within the daily budget,
  or reopen the paid-key question.
- Google changes the free-tier limits materially in either direction.
- A second machine or a larger GPU makes a larger local model viable.
