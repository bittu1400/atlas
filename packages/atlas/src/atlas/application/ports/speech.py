"""Port interface for Speech and Audio Narration (Defined, Unimplemented Seam).

As specified in SPEC §2, §4.1, and Decision D3:
- ORIGINS videos use silent kinetic text + sound design (no narration).
- The Speech port is formally defined so long-form or future narrated channels cost nothing to add.
"""

from typing import Protocol


class Speech(Protocol):
    """Port for text-to-speech narration synthesis (seam for future phases)."""

    async def synthesize(self, text: str, voice_id: str) -> tuple[bytes, float]:
        """Synthesize text into audio bytes and duration in seconds."""
        ...
