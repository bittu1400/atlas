import asyncio

from atlas.application.ports.media import ImageGenerator


class LocalStableDiffusionGenerator(ImageGenerator):
    """Local Stable Diffusion implementation of ImageGenerator (Tier 1)."""

    def __init__(self) -> None:
        # Enforce single GPU access to prevent OOM
        self._gpu_semaphore = asyncio.Semaphore(1)

    async def generate_image(self, prompt: str, aspect_ratio: str = "1:1") -> tuple[bytes, str]:
        """Generate an image using local Stable Diffusion."""
        await self._gpu_semaphore.acquire()
        try:
            # TODO: Integrate actual diffusers pipeline here when dependencies are added.
            # This acts as a structural implementation enforcing the GPU lock constraint.
            await asyncio.sleep(0.1)

            content = f"STABLE_DIFFUSION_BYTES_FOR:{prompt}:{aspect_ratio}".encode()
            mime_type = "image/png"

            # Note: Invariant 9 (is_ai_generated=True) must be enforced by the caller
            # when persisting this asset to the database, triggering the manual approval gate.
            return content, mime_type
        finally:
            self._gpu_semaphore.release()
