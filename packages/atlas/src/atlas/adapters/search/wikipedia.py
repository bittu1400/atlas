"""Wikipedia search adapter conforming to Search port."""

import httpx
from atlas.application.ports.search import Search, SearchResultItem
from atlas.platform.errors import AtlasError


class WikipediaSearch(Search):
    """Tier 0 search adapter querying Wikipedia public API for encyclopedic and historical sources."""

    def __init__(
        self,
        user_agent: str = "AtlasKnowledgeBot/0.1.0 (https://github.com/atlas)",
        timeout_seconds: float = 10.0,
    ) -> None:
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds

    async def search(
        self, query: str, limit: int = 10, allowlist: list[str] | None = None
    ) -> list[SearchResultItem]:
        """Search Wikipedia for relevant articles and extracts."""
        api_url = "https://en.wikipedia.org/w/api.php"
        params: dict[str, str | int] = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": min(limit, 50),
            "format": "json",
            "utf8": 1,
        }
        headers = {"User-Agent": self.user_agent}

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.get(api_url, params=params, headers=headers)
                resp.raise_for_status()
                data = resp.json()

                search_hits = data.get("query", {}).get("search", [])
                results: list[SearchResultItem] = []

                for item in search_hits:
                    title = item.get("title", "")
                    page_id = item.get("pageid", 0)
                    snippet = (
                        item.get("snippet", "")
                        .replace('<span class="searchmatch">', "")
                        .replace("</span>", "")
                    )
                    url = f"https://en.wikipedia.org/?curid={page_id}"

                    if allowlist and not any(allowed in url for allowed in allowlist):
                        continue

                    results.append(
                        SearchResultItem(
                            title=title,
                            url=url,
                            snippet=snippet,
                            source_name="Wikipedia",
                        )
                    )

                return results

        except Exception as exc:
            # Fall back gracefully to empty list on network failure or timeout
            raise AtlasError(f"Wikipedia search failed for '{query}': {exc}") from exc
