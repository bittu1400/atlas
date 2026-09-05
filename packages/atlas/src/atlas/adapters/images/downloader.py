import hashlib

import httpx
from atlas.application.ports.storage import Storage


class UnsupportedMimeTypeError(Exception):
    """Raised when an unsupported image MIME type is encountered."""

    pass


class ImageDownloader:
    """Utility class for downloading and storing images."""

    def __init__(self, storage: Storage, client: httpx.AsyncClient | None = None) -> None:
        self.storage = storage
        self.client = client or httpx.AsyncClient(timeout=30.0)

    async def download(self, url: str) -> str:
        """Download image from URL, verify MIME type, and store content-addressed."""
        res = await self.client.get(url, follow_redirects=True)
        res.raise_for_status()

        content = res.content
        mime_type = res.headers.get("content-type", "").lower().split(";")[0]

        if mime_type not in ("image/jpeg", "image/png", "image/webp"):
            if content.startswith(b"\xff\xd8\xff"):
                mime_type = "image/jpeg"
            elif content.startswith(b"\x89PNG\r\n\x1a\n"):
                mime_type = "image/png"
            elif content.startswith(b"RIFF") and b"WEBP" in content[8:12]:
                mime_type = "image/webp"
            else:
                raise UnsupportedMimeTypeError(f"Unsupported MIME type: {mime_type}")

        # Compute SHA-256 for idempotency check (assuming storage key is the hash)
        sha256 = hashlib.sha256(content).hexdigest()

        if await self.storage.exists(sha256):
            return sha256

        return await self.storage.put(content, mime_type=mime_type)
