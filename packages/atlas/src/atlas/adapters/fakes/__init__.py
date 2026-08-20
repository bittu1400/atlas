"""Deterministic provider doubles for hermetic tests and zero-cost local execution."""

from atlas.adapters.fakes.providers import (
    FakeEmbedder,
    FakeImageGenerator,
    FakeImageSearch,
    FakeLlm,
    FakeNotifier,
    FakePublisher,
    FakeQueueBroker,
    FakeRenderer,
    FakeSearch,
    FakeSoundLibrary,
    FakeSourceFetcher,
    FakeSpeech,
)

__all__ = [
    "FakeEmbedder",
    "FakeImageGenerator",
    "FakeImageSearch",
    "FakeLlm",
    "FakeNotifier",
    "FakePublisher",
    "FakeQueueBroker",
    "FakeRenderer",
    "FakeSearch",
    "FakeSoundLibrary",
    "FakeSourceFetcher",
    "FakeSpeech",
]
