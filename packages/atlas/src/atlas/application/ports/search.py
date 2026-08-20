"""Port interface for primary source web & academic search."""

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


class SearchResultItem(BaseModel):
    """An individual search hit from a primary source repository."""

    model_config = ConfigDict(frozen=True)

    title: str = Field(description="Document title")
    url: str = Field(description="Document URL or permalink")
    snippet: str = Field(description="Contextual text snippet")
    source_name: str = Field(description="Originating repository or publication")


class Search(Protocol):
    """Port for discovering primary literature and archival sources."""

    async def search(
        self, query: str, limit: int = 10, allowlist: list[str] | None = None
    ) -> list[SearchResultItem]:
        """Perform search constrained by optional domain allowlist."""
        ...
