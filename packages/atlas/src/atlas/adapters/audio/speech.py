from atlas.application.ports.speech import Speech


class NoOpSpeech(Speech):
    """Production seam for speech synthesis (Phase 9). Returns empty audio bytes."""

    async def synthesize(self, text: str, voice_id: str) -> tuple[bytes, float]:
        """Return zero bytes and 0.0 duration."""
        return b"", 0.0
