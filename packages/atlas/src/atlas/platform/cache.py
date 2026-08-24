"""Deterministic Response Caching for Model Invocations.

As specified in ADR-0004:
- Response caching keyed on input hash + prompt version + model + parameters.
- Retries and re-renders cost zero quota and are exactly reproducible.
"""

import hashlib
import json
import threading
from collections import OrderedDict
from typing import Any


class ResponseCache:
    """Bounded, thread-safe LRU deterministic response cache for LLM outputs."""

    def __init__(self, maxsize: int = 1000) -> None:
        if maxsize <= 0:
            raise ValueError("maxsize must be greater than 0")
        self.maxsize = maxsize
        self._cache: OrderedDict[str, str] = OrderedDict()
        self._lock = threading.Lock()

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
        """Retrieve cached response string if present, marking as recently used."""
        with self._lock:
            if cache_key in self._cache:
                self._cache.move_to_end(cache_key)
                return self._cache[cache_key]
            return None

    def set(self, cache_key: str, response_content: str) -> None:
        """Store response in cache, evicting oldest entry if capacity is reached."""
        with self._lock:
            if cache_key in self._cache:
                self._cache.move_to_end(cache_key)
            self._cache[cache_key] = response_content
            if len(self._cache) > self.maxsize:
                self._cache.popitem(last=False)

    def clear(self) -> None:
        """Clear cache contents."""
        with self._lock:
            self._cache.clear()

    def __len__(self) -> int:
        """Return current cache size."""
        with self._lock:
            return len(self._cache)
