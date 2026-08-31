"""Port interface for text embeddings."""

from typing import Protocol


class Embedder(Protocol):
    """Port for generating dense semantic vector embeddings."""

    @property
    def dimension(self) -> int:
        """Vector dimensionality (e.g. 768)."""
        ...

    @property
    def provider(self) -> str:
        """Provider name recorded on the `model_calls` row (Invariant 7)."""
        ...

    @property
    def model_id(self) -> str:
        """Model identifier recorded on the `model_calls` row (Invariant 7)."""
        ...

    async def embed(self, text: str) -> list[float]:
        """Embed a single text string."""
        ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of text strings."""
        ...
