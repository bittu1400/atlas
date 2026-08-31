"""Stub AI image generator.

Rule R3: no diffusers pipeline is loaded and no image is synthesised. What is
real is the GPU lease discipline (ADR-0001): the semaphore is held for the
duration of a generation, so the seam behaves correctly when a real model is
dropped in. Any asset produced here is still `is_ai_generated=True` and still
needs the Invariant 9 human approval before it can reach a render.
"""

import asyncio

from atlas.application.ports.media import ImageGenerator

PLACEHOLDER_PREFIX = b"PLACEHOLDER_IMAGE_BYTES"


class StubImageGenerator(ImageGenerator):
    """Holds the GPU lease and returns obviously synthetic placeholder bytes."""

    def __init__(self) -> None:
        # Enforce single GPU access to prevent OOM
        self._gpu_semaphore = asyncio.Semaphore(1)

    async def generate_image(self, prompt: str, aspect_ratio: str = "1:1") -> tuple[bytes, str]:
        """Return placeholder bytes while holding the single-slot GPU lease."""
        async with self._gpu_semaphore:
            await asyncio.sleep(0.1)
            content = PLACEHOLDER_PREFIX + f":{prompt}:{aspect_ratio}".encode()
            return content, "image/png"
