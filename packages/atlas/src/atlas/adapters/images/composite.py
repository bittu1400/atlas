from atlas.application.ports.media import ImageCandidate, ImageSearch


class CompositeImageSearch(ImageSearch):
    """Composite ImageSearch that delegates to multiple searchers in order."""

    def __init__(self, searchers: list[ImageSearch]) -> None:
        self.searchers = searchers

    async def search_archival(self, query: str, limit: int = 10) -> list[ImageCandidate]:
        """Search across all configured repositories."""
        results = []
        urls_seen = set()

        for searcher in self.searchers:
            remaining = limit - len(results)
            if remaining <= 0:
                break

            try:
                candidates = await searcher.search_archival(query, limit=remaining)
            except Exception:
                continue

            for cand in candidates:
                if cand.url not in urls_seen:
                    urls_seen.add(cand.url)
                    results.append(cand)
                    if len(results) >= limit:
                        return results

        return results
