# ADR 0009: Phase 6 Production Integration & Dependency Injection

**Status:** Accepted
**Date:** 2026-08-26

## Context and Problem Statement

Phases 1 through 5 built the core domain logic, state machine, frontend, and intelligence agents. However, the application entrypoints (`main.py`, `tasks.py`, `cli.py`) were still hardcoding `Fake*` providers to allow testing to pass. The architecture required a way to structurally enforce that production runs use real providers (Gemini, Ollama, Freesound, Remotion) while tests remain deterministic, fast, and offline.

Additionally, Phase 6 required implementing the real outer adapters for media (audio and images) and publishing without violating the zero-budget constraint (ADR-0004) and keeping the scope manageable for the Phase 7 end-to-end milestone.

## Decision Drivers

- **Zero Fakes in Production:** A hard architectural constraint that fakes must never leak into the live environment.
- **Test Determinism:** 98 tests must continue to run in < 10 seconds without hitting external APIs.
- **Zero Budget Constraint (ADR-0004):** We cannot use paid APIs for media retrieval.
- **Narrative Format (D3):** On-screen kinetic text and sound design, no voiceover.

## Considered Options

1. **Environment Variable Feature Flags:** Toggle fakes vs. real providers via `USE_FAKES=true`.
2. **Global Dependency Injection Container:** A single configuration module that wires up the production dependencies, which tests can explicitly mock.
3. **Paid Asset APIs:** Use Epidemic Sound or Storyblocks for audio, and Getty for images.
4. **Public Domain / CC0 Assets:** Use Freesound for audio, Wikimedia Commons/Internet Archive for images, and local Stable Diffusion for fallbacks.

## Decision Outcome

**Chosen option: Option 2 (DI Container) and Option 4 (CC0 Assets).**

### 1. Unified Dependency Injection Container (D45)
We implemented a centralized `Container` in `packages/atlas/src/atlas/adapters/container.py`. 
- The FastAPI app, Dramatiq worker, and Typer CLI now instantiate this container and resolve all ports through it.
- The container wires up real adapters: `GeminiLlm`, `OllamaLlm`, `DramatiqQueueBroker`, `RemotionRenderer`, etc.
- In tests, we override these dependencies using FastAPI's `dependency_overrides` and pytest fixtures, guaranteeing that the production code path has absolutely zero awareness of test fakes.

### 2. Audio Strategy (Freesound & NoOpSpeech) (D46)
Since D3 mandates no voiceover, we implemented `NoOpSpeech` for the `Speech` port. This preserves the architectural seam for future voiceovers without shipping test code (`FakeSpeech`) to production. 
For sound design, we integrated the **Freesound API** (`FreesoundLibrary`) strictly querying the `license:"Creative Commons 0"` subset, ensuring all audio is genuinely public domain.

### 3. Visual Strategy (Archival & Local SD)
We built `WikimediaCommonsSearch` and `InternetArchiveSearch` to source historical public domain imagery, matching the ORIGINS channel focus. We wrapped these in a `CompositeImageSearch`. For AI image fallbacks, we implemented `LocalStableDiffusionGenerator` using the existing GPU semaphore to prevent OOM errors alongside Ollama.

### 4. Publishing Stub
We implemented a `YouTubePublisher` mock. True OAuth2 YouTube integration is deferred to Phase 8, as the immediate goal of Phase 7 is producing the final RenderArtifact locally.

## Consequences

- **Positive:** Production entrypoints are strictly clean of test fakes.
- **Positive:** All media is verifiably public domain or locally generated, preserving the zero-budget and licensing constraints.
- **Negative/Risk:** The Freesound API rate limits and search relevancy might require fine-tuning the `SoundDesignAgent`.
- **Negative/Risk:** The DI container introduces a small amount of boilerplate, but it's isolated to one file.
