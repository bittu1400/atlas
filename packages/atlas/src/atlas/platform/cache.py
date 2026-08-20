"""Deterministic Response Caching for Model Invocations.

As specified in ADR-0004:
- Response caching keyed on input hash + prompt version + model + parameters.
- Retries and re-renders cost zero quota and are exactly reproducible.
"""

import hashlib
import json
from typing import Any


class ResponseCache:
    """In-memory and deterministic response cache for LLM outputs."""

    def __init__(self) -> None:
        self._cache: dict[str, str] = {}

    @staticmethod
    def compute_cache_key(
        prompt: str,
        prompt_version: str,
        model_id: str,
        parameters: dict[str, Any],
    ) -> str:
        """Compute SHA-256 cache key from call inputs."""
        serialized_params = json.dumps(parameters, sort_keys=True)
        raw_key = f"{prompt}|{prompt_version}|{model_id}|{serialized_params}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def get(self, cache_key: str) -> str | None:
        """Retrieve cached response string if present."""
        return self._cache.get(cache_key)

    def set(self, cache_key: str, response_content: str) -> None:
        """Store response in cache."""
        self._cache[cache_key] = response_content

    def clear(self) -> None:
        """Clear cache contents."""
        self._cache.clear()
