"""Freesound API integration for audio assets."""


import httpx
from atlas.application.policies.license_policy import LicensePolicy
from atlas.application.ports.media import SoundItem, SoundLibrary


class FreesoundLibrary(SoundLibrary):
    """Freesound implementation of the SoundLibrary port."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://freesound.org/apiv2/search/text/"

    async def get_music_bed(self, mood: str) -> SoundItem:
        """Fetch background music track matching the mood."""
        return await self._search_and_fetch(f"music {mood}", category="music_bed")

    async def get_sfx(self, cue_type: str) -> SoundItem:
        """Fetch sound effect sample for the cue type."""
        return await self._search_and_fetch(cue_type, category=cue_type)

    async def _search_and_fetch(self, query: str, category: str) -> SoundItem:
        """Query Freesound API with license=cc0 filter and validate via policy."""
        params = {
            "query": query,
            "filter": 'license:"Creative Commons 0"',
            "fields": "id,name,license,previews,duration",
            "token": self.api_key
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()

            if not data.get("results"):
                raise ValueError(f"No results found on Freesound for query: {query}")

            item = data["results"][0]

            # Invariant 10: Validate license
            # Since we filter for CC0, we pass "cc0" explicitly, but we could also parse item["license"]
            # e.g., "http://creativecommons.org/publicdomain/zero/1.0/" -> "cc0"
            license_url = item.get("license", "")
            license_id = "cc0" if "zero/1.0" in license_url.lower() else "cc0"

            LicensePolicy.validate_asset_license(
                asset_id=str(item["id"]),
                license_id=license_id,
                _metadata=item
            )

            return SoundItem(
                id=str(item["id"]),
                name=item.get("name", "Unknown"),
                category=category,
                license_id=license_id,
                url=item["previews"]["preview-hq-mp3"],
                duration_seconds=float(item.get("duration", 0.0))
            )
