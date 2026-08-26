"""Thumbnail generator adapter."""


class ThumbnailGenerator:
    """Dummy thumbnail generator."""

    async def generate(self) -> str:
        """Generate a dummy thumbnail."""
        return "thumbnail_mock_id_123"
