"""Top-level fakes package re-exporting deterministic provider doubles."""

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
