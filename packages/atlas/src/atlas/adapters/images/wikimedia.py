import asyncio
from typing import Any
from uuid import uuid4

import httpx
from atlas.application.policies.license_policy import LicensePolicy
from atlas.application.ports.media import ImageCandidate, ImageSearch
from atlas.platform.errors import LicenseIncompatibleError


class WikimediaCommonsSearch(ImageSearch):
    """Wikimedia Commons implementation of ImageSearch."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.client = client or httpx.AsyncClient(
            headers={"User-Agent": "Atlas-Documentary-Bot/1.0 (https://github.com/bittusah/atlas)"},
            timeout=10.0,
        )
        self.base_url = "https://commons.wikimedia.org/w/api.php"
        self._rate_limit_lock = asyncio.Lock()
        self._last_request_time = 0.0

    async def _polite_get(self, params: dict[str, Any]) -> dict[str, Any]:
        async with self._rate_limit_lock:
            now = asyncio.get_running_loop().time()
            elapsed = now - self._last_request_time
            if elapsed < 1.0:
                await asyncio.sleep(1.0 - elapsed)

            res = await self.client.get(self.base_url, params=params)
            res.raise_for_status()
            self._last_request_time = asyncio.get_running_loop().time()
            return res.json()  # type: ignore[no-any-return]

    async def search_archival(self, query: str, limit: int = 10) -> list[ImageCandidate]:
        """Search Wikimedia Commons for images matching the query."""
        search_params = {
            "action": "query",
            "list": "search",
            "srnamespace": "6",
            "srsearch": query,
            "format": "json",
            "srlimit": min(limit * 2, 50),
        }
        search_data = await self._polite_get(search_params)
        titles = [item["title"] for item in search_data.get("query", {}).get("search", [])]
        if not titles:
            return []

        # Split titles into chunks of 50 (API limit)
        candidates = []
        for i in range(0, len(titles), 50):
            chunk = titles[i : i + 50]
            meta_params = {
                "action": "query",
                "prop": "imageinfo",
                "iiprop": "extmetadata|url",
                "titles": "|".join(chunk),
                "format": "json",
            }
            meta_data = await self._polite_get(meta_params)

            pages = meta_data.get("query", {}).get("pages", {})
            for page_id, page in pages.items():
                if page_id == "-1":
                    continue

                imageinfo = page.get("imageinfo")
                if not imageinfo:
                    continue
                info = imageinfo[0]
                ext = info.get("extmetadata", {})

                title = page.get("title", "")
                url = info.get("url", "")
                if not url:
                    continue

                license_str = (
                    ext.get("LicenseShortName", {}).get("value", "")
                    or ext.get("UsageTerms", {}).get("value", "")
                    or "Unknown"
                )
                author = ext.get("Artist", {}).get("value", "Unknown Author")

                candidate = ImageCandidate(
                    id=str(uuid4()),
                    title=title,
                    url=url,
                    license_id=license_str,
                    author=author,
                    source_archive="Wikimedia Commons",
                    preview_url=info.get("url"),
                )

                try:
                    LicensePolicy.validate_asset_license(candidate.id, candidate.license_id)
                    candidates.append(candidate)
                    if len(candidates) >= limit:
                        return candidates
                except LicenseIncompatibleError:
                    continue

        return candidates
