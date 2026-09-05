import asyncio
from typing import Any
from uuid import uuid4

import httpx
from atlas.application.policies.license_policy import LicensePolicy
from atlas.application.ports.media import ImageCandidate, ImageSearch
from atlas.platform.errors import LicenseIncompatibleError


class InternetArchiveSearch(ImageSearch):
    """Internet Archive implementation of ImageSearch."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.client = client or httpx.AsyncClient(
            headers={"User-Agent": "Atlas-Documentary-Bot/1.0 (https://github.com/bittusah/atlas)"},
            timeout=10.0,
        )
        self.search_url = "https://archive.org/advancedsearch.php"
        self.metadata_url = "https://archive.org/metadata/"
        self._rate_limit_lock = asyncio.Lock()
        self._last_request_time = 0.0

    async def _polite_get(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        async with self._rate_limit_lock:
            now = asyncio.get_running_loop().time()
            elapsed = now - self._last_request_time
            if elapsed < 1.0:
                await asyncio.sleep(1.0 - elapsed)

            res = await self.client.get(url, params=params)
            res.raise_for_status()
            self._last_request_time = asyncio.get_running_loop().time()
            return res.json()  # type: ignore[no-any-return]

    async def search_archival(self, query: str, limit: int = 10) -> list[ImageCandidate]:
        """Search Internet Archive for images matching the query."""
        # Only ask for items that declare a license. Without this the search
        # returned mostly `licenseurl`-less items, which Invariant 10 rejects,
        # so the adapter spent up to 31 seconds of polite metadata fetches per
        # call to return an empty list every time (defect V-10).
        search_params = {
            "q": f"{query} AND mediatype:image AND licenseurl:[* TO *]",
            "fl[]": ["identifier"],
            "output": "json",
            "rows": limit * 3,
        }
        search_data = await self._polite_get(self.search_url, search_params)
        docs = search_data.get("response", {}).get("docs", [])
        if not docs:
            return []

        candidates = []
        for doc in docs:
            identifier = doc.get("identifier")
            if not identifier:
                continue

            try:
                meta_data = await self._polite_get(f"{self.metadata_url}{identifier}")
            except httpx.HTTPError:
                continue

            metadata = meta_data.get("metadata", {})
            files = meta_data.get("files", [])

            # Find an image file
            image_file = None
            for file in files:
                fmt = file.get("format", "")
                if ("JPEG" in fmt or "PNG" in fmt) and "Thumb" not in fmt:
                    image_file = file.get("name")
                    break

            if not image_file:
                continue

            url = f"https://archive.org/download/{identifier}/{image_file}"
            preview_url = f"https://archive.org/services/img/{identifier}"

            # IA often uses licenseurl or collection (like NASA)
            license_str = metadata.get("licenseurl") or metadata.get("license") or "Unknown"

            # Special case for collections known to be public domain but lacking explicit license metadata
            collections = metadata.get("collection", [])
            if isinstance(collections, str):
                collections = [collections]

            if license_str == "Unknown" and any("nasa" in c.lower() for c in collections):
                license_str = "pd"

            author = metadata.get("creator", "Unknown Author")
            if isinstance(author, list):
                author = ", ".join(author)

            candidate = ImageCandidate(
                id=str(uuid4()),
                title=metadata.get("title", identifier),
                url=url,
                license_id=license_str,
                author=author,
                source_archive="Internet Archive",
                preview_url=preview_url,
                is_ai_generated=False,
            )

            try:
                LicensePolicy.validate_asset_license(candidate.id, candidate.license_id)
                candidates.append(candidate)
                if len(candidates) >= limit:
                    break
            except LicenseIncompatibleError:
                continue

        return candidates
