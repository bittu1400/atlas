# ADR-0006 — The Timing Plan as canonical pacing artifact

**Status:** Accepted
**Date:** 2026-07-30
**Relates to:** D32, D5, D3

## Context

Removing narration removes the thing that normally dictates pacing for free. In a narrated video the
voice track is the clock: subtitles align to it, cuts follow it, and music sits under it. Without a voice,
**pacing has to be authored**, and there is nothing to hide behind — a video that reveals text too fast is
unreadable, and one that holds too long is dead air with pictures.

Four systems need to agree exactly: text reveal animation, sound effects, visual cuts, and captions. If
each computes its own timing from the Script, they will drift, and drift in this format is immediately
visible as text appearing after the sound that announces it.

Duration is also an operator input with a 60-second default, so timing must *fit* a target rather than
accumulate to whatever total the Script happens to produce.

## Decision

**The Timing Plan is a first-class, versioned artifact. It is computed once from the Script and the Style
Profile, and every downstream system reads from it. Nothing recomputes timing independently.**

1. **Single source of truth.** Text animation, SFX placement, cut points, and WebVTT captions all derive
   from the Timing Plan. Drift becomes structurally impossible rather than a bug to chase.
2. **Fitting, not accumulation.** Given N Beats and a target duration, the plan solves for reveal rate and
   hold duration per Beat subject to constraints: minimum legible hold, maximum reveal rate, and total
   duration within ±2 seconds of target. If no solution exists, it fails loudly with a specific reason —
   too many Beats, or too many words for the duration — and routes back to the Script stage rather than
   silently producing something unreadable.
3. **Grounded in reading speed, not speech.** Constants derive from silent reading comprehension —
   roughly 2.0–2.5 effective words per second once dwell time is included — and live in the Channel's
   Style Profile as tunable values, never as literals in code.
4. **Emphasis costs time.** A Beat marked for emphasis receives additional hold. Pacing variation is what
   separates edited work from metronomic output, and it has to be expressible in the model.
5. **Beat-to-music alignment.** When a music bed with a known tempo is selected, cut points snap to the
   nearest beat within a tolerance window. Cuts landing on the beat is most of what makes this format feel
   deliberate rather than assembled.
6. **Captions are exported, not transcribed.** WebVTT is generated directly from the plan, so it is
   frame-accurate by construction. The Subtitle Builder from `prompt.md` collapses to a trivial exporter,
   which is a genuine simplification the format buys us.
7. **Sound design reads the plan.** Keystroke texture is placed on reveal events with randomized velocity
   and timbre variation. A fixed sample repeated identically on every reveal sounds mechanical and fails
   the quality gate.
8. **Pure and testable.** The fitting algorithm is domain logic with no I/O — deterministic, unit-testable
   with property tests over word counts and durations, and never a model call. Pacing is arithmetic, not
   inference.

## Alternatives considered

**Fixed seconds per Beat.** Trivial to implement. Rejected because a four-word Beat and a twelve-word Beat
need different time, and uniform pacing is exactly the mechanical rhythm the quality bar rejects.

**Let each system compute its own timing from the Script.** No new artifact required. Rejected because
four independent implementations of the same calculation will diverge, and the divergence is visible in
the output.

**Ask a model to produce the timing.** Tempting, and it would handle emphasis with some taste. Rejected on
three grounds: it spends Tier 2 quota on arithmetic, it is non-deterministic so renders stop being
reproducible, and it cannot guarantee the hard constraint of landing within ±2 seconds of target. The
model's judgment belongs in the Script — which Beats, which words, which emphasis — not in the schedule.

**Generate timing during rendering, inside the Remotion composition.** Convenient and keeps it near the
animation. Rejected because it would trap pacing inside the renderer, making it invisible to the quality
gate, unavailable to the sound designer, and coupled to a specific `Renderer` adapter.

## Consequences

- Audio, text, cuts, and captions are guaranteed synchronized because they read identical data.
- Duration is honored exactly, so the operator's length input actually controls output length.
- The quality gate can inspect pacing directly — average hold, variance, reveal rate — and score it.
- An impossible fit is caught before rendering, which saves a GPU lease and an entire render cycle.
- The Script agent gains a hard constraint it must respect: a Script that cannot be fitted is rejected,
  which usefully forces tighter writing.
- Style Profile pacing constants become a tuning surface, and the right values will be found empirically
  over the first several videos.

## Trade-offs accepted

Pacing decided by a deterministic algorithm will be less nuanced than a skilled human editor's judgment,
and some Beats will get time they do not deserve while others feel rushed. We accept that in exchange for
determinism, reproducibility, zero quota cost, and a hard duration guarantee. The escape hatch is manual
per-Beat dwell overrides at the Script approval gate, where a human is already looking — human taste
enters as an input to the algorithm rather than replacing it.

## Revisit when

- Quality scores consistently mark pacing as the weakest dimension despite constant tuning.
- Manual dwell overrides become routine rather than occasional, which would indicate the algorithm is
  systematically wrong.
- Durations extend to several minutes, where narrative rhythm at a larger scale — chapters, movements,
  tension curves — may need modelling above the Beat level.
