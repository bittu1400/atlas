# ADR-0005 — Remotion as the primary renderer

**Status:** Accepted
**Date:** 2026-07-30
**Relates to:** D31, D5b, D33

## Context

The output format has no narration. On-screen kinetic text carries the entire story, over public-domain
archival stills with slow motion treatment, cut to music, with sound design supplying physicality.

This inverts the usual priority: **typography is not decoration here, it is the product.** Per-word
reveals, precise kerning, responsive line breaking, and emphasis all have to be excellent, and they have
to be excellent at two aspect ratios — 9:16 for the Shorts surface where 60-second content is discovered,
and 16:9 for traditional YouTube and the path to long-form.

`prompt.md` lists FFmpeg as the renderer and Remotion as a future consideration. The format decision
inverts that ordering, which is why this ADR exists.

FFmpeg's `drawtext` cannot do per-word reveals, has no real layout engine, no kerning control, and no
responsive line breaking. Achieving this format with it means generating frames externally anyway, at
which point FFmpeg is a compositor rather than a renderer — which is exactly the role it should keep.

## Decision

**Remotion is the primary renderer, behind a `Renderer` port. FFmpeg remains the compositor and the
audio-mux stage.**

- Compositions are React components in `apps/renderer/`, driven by the Storyboard and the Timing Plan.
- **Layout is responsive from the first component.** Text safe areas, type scale, and image crop focal
  points are computed per Render Target. No component hardcodes a position or a pixel size. This is the
  single most important implementation rule in the renderer, because retrofitting a second aspect ratio
  into positioned components is a rewrite.
- Design tokens live in `packages/tokens/` as one JSON source consumed by both the dashboard and the
  compositions, so the product and its output cannot drift apart visually.
- FFmpeg handles audio mixing, loudness normalization to −14 LUFS, and container muxing.
- The `Renderer` port means an FFmpeg-only or HTML-frames implementation can be added without touching
  anything above `adapters/`.

## Alternatives considered

**Pure FFmpeg.** Zero additional dependencies, no license question, fastest raw throughput, and already
installed. Rejected because per-word text animation with correct typography is not achievable in
`drawtext` without descending into per-frame filter generation — brittle, unreadable, and untestable. For
a format where text *is* the content, this is the wrong tool.

**HTML frames via Playwright plus FFmpeg.** Fully free forever with no licensing ceiling, full CSS
typography, and Chromium is a dependency Remotion brings anyway. It was the strongest alternative and
remains the designated exit path. Rejected as primary because Atlas would have to build the timeline
abstraction, interpolation, frame sequencing, and preview tooling that Remotion already provides and
tests — weeks of work reproducing a solved problem.

**Motion Canvas.** MIT licensed with no company-size ceiling, purpose-built for programmatic motion
graphics. A genuinely good option. Rejected because its ecosystem, documentation, and asset-handling
maturity are behind Remotion's, and because it does not share component idioms with the React dashboard,
which forfeits the shared-token benefit.

**A Python renderer such as MoviePy or manim.** Keeps the stack single-language. Rejected on typography:
neither offers a real text layout engine, and manim's abstractions target mathematical animation rather
than editorial motion design.

## Consequences

- Text animation quality is high from the start, and iteration is fast because compositions preview live
  in a browser.
- Node and pnpm join a Python-primary stack, and CI must build both.
- Design tokens are shared between dashboard and video — a real, ongoing benefit unique to this choice.
- Remotion renders through headless Chromium, which contends with Tier 1 inference for the same 8 GB GPU.
  Rendering therefore acquires the GPU lease from ADR-0001 rather than running concurrently with local
  models.
- Both Render Targets come from one composition, so adding a target later is a configuration entry.
- Render time and resource use must be measured against the ≤ 5 minutes per target target in `docs/SPEC.md`.

## Trade-offs accepted

**Licensing.** Remotion is free for individuals and small teams but requires a paid company license above
a small headcount. Atlas is a solo project today, so it is free — but `prompt.md` frames this as the
foundation of a long-term company, and that is a future cost, not a hypothetical one. We accept it
deliberately because the `Renderer` port keeps the exit cheap, and because the HTML-frames alternative
remains implementable at any time. **This is the one dependency in the stack with a commercial ceiling and
it should be reviewed before any team growth.**

We also accept a second language runtime in the stack, slower rendering than raw FFmpeg, and Chromium's
memory footprint on a laptop.

## Revisit when

- Atlas becomes a company with employees, at which point the license must be evaluated against building
  out the HTML-frames adapter.
- Render time exceeds the 5-minute target per Render Target.
- Chromium's GPU contention with Tier 1 models proves unmanageable even when serialized.
- A format arrives that Remotion serves poorly — for example, heavy real footage editing rather than
  motion graphics over stills.
