"""Polite HTTP Source Fetcher adapter with SHA-256 snapshotting."""

import hashlib
import mimetypes

import httpx
from atlas.application.ports.sources import SourceFetcher
from atlas.platform.errors import AtlasError


class SourceFetchError(AtlasError):
    """Raised when an external source fails to fetch."""

    def __init__(self, url: str, reason: str) -> None:
        super().__init__(f"Failed to fetch primary source from '{url}': {reason}")
        self.url = url
        self.reason = reason


class HttpSourceFetcher(SourceFetcher):
    """Polite HTTP client for retrieving Tier 0 primary source documents and archives."""

    def __init__(
        self,
        user_agent: str = "AtlasKnowledgeBot/0.1.0 (+https://github.com/atlas; academic research)",
        timeout_seconds: float = 15.0,
    ) -> None:
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds

    async def fetch(self, url: str) -> tuple[bytes, str, str]:
        """Fetch URL content, returning (content_bytes, sha256_hash, mime_type).

        Enforces SHA-256 content addressing for immutable storage.
        """
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml,text/plain,application/json;q=0.9,*/*;q=0.8",
        }

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds, follow_redirects=True
            ) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()

                content_bytes = response.content
                sha256_hash = hashlib.sha256(content_bytes).hexdigest()

                # Determine MIME type from Content-Type header or URL
                content_type = response.headers.get("content-type", "")
                mime_type = content_type.split(";")[0].strip() if content_type else ""

                if not mime_type or mime_type == "application/octet-stream":
                    guessed, _ = mimetypes.guess_type(url)
                    mime_type = guessed or "text/plain"

                return content_bytes, sha256_hash, mime_type

        except httpx.HTTPStatusError as exc:
            raise SourceFetchError(url, f"HTTP {exc.response.status_code}") from exc
        except httpx.RequestError as exc:
            raise SourceFetchError(url, str(exc)) from exc
        except Exception as exc:
            raise SourceFetchError(url, f"Unexpected error: {exc}") from exc
