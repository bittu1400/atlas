"""Port interfaces for Archival Image Search, Image Generation, and Sound."""

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


class ImageCandidate(BaseModel):
    """Archival image candidate discovered from repositories."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Unique candidate ID")
    title: str = Field(description="Title / description of the image")
    url: str = Field(description="Direct URL to image file")
    license_id: str = Field(description="License identifier (e.g. CC-BY-4.0, Public Domain)")
    author: str = Field(description="Author / photographer / creator attribution")
    source_archive: str = Field(description="Origin archive (e.g. Wikimedia Commons, Smithsonian)")
    preview_url: str | None = Field(default=None, description="Low-res thumbnail URL")


class SoundItem(BaseModel):
    """Audio asset discovered or loaded from sound library."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Sound asset identifier")
    name: str = Field(description="Asset title / description")
    category: str = Field(description="Audio category (music_bed, keystroke, transition, ambient)")
    license_id: str = Field(description="License identifier (e.g. CC0, CC-BY)")
    url: str = Field(description="Audio file URL or local path")
    duration_seconds: float = Field(ge=0.0, description="Audio duration in seconds")


class ImageSearch(Protocol):
    """Port for finding archival imagery across public domain and libre repositories."""

    async def search_archival(self, query: str, limit: int = 10) -> list[ImageCandidate]:
        """Search archival collections for matching imagery."""
        ...


class ImageGenerator(Protocol):
    """Port for local AI image generation (priority 4, always requiring human approval)."""

    async def generate_image(self, prompt: str, aspect_ratio: str = "1:1") -> tuple[bytes, str]:
        """Generate image bytes and mime type from prompt."""
        ...


class SoundLibrary(Protocol):
    """Port for sound design assets (keystroke variations, ambient beds, transitions)."""

    async def get_music_bed(self, mood: str) -> SoundItem:
        """Fetch background music track."""
        ...

    async def get_sfx(self, cue_type: str) -> SoundItem:
        """Fetch sound effect sample."""
        ...
