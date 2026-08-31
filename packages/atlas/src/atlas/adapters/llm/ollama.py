"""Ollama local LLM adapter implementing Llm and StructuredLlm ports.

As specified in ADR-0004 & Invariant 5:
- Local GPU inference for Tier 1 transformation tasks.
- Handles JSON structured format parsing, token estimating, and error recovery.
"""

import json
import time
from typing import Any, TypeVar

import httpx
from atlas.application.ports.embedder import Embedder
from atlas.application.ports.llm import (
    Extracted,
    Llm,
    LlmCapabilities,
    LlmRequest,
    LlmResponse,
    StructuredLlm,
)
from atlas.platform.errors import AtlasError
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class OllamaProviderError(AtlasError):
    """Raised when Ollama server fails to respond or returns invalid payload."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Ollama provider error: {message}")


class OllamaLlm(Llm, StructuredLlm):
    """Tier 1 local LLM adapter querying Ollama HTTP daemon."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model_id: str = "qwen3:8b",
        timeout_seconds: float = 60.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_id = model_id
        self.timeout_seconds = timeout_seconds
        self._capabilities = LlmCapabilities(
            tier=1,
            supports_json=True,
            supports_vision=False,
            context_window_tokens=32768,
            rpm_limit=1000,
            rpd_limit=100_000,
        )

    @property
    def capabilities(self) -> LlmCapabilities:
        return self._capabilities

    async def complete(self, request: LlmRequest) -> LlmResponse:
        """Generate completion from local Ollama model."""
        url = f"{self.base_url}/api/generate"
        payload: dict[str, Any] = {
            "model": self.model_id,
            "prompt": request.prompt,
            "stream": False,
            "options": {
                "temperature": request.temperature,
            },
        }
        if request.system_prompt:
            payload["system"] = request.system_prompt
        if request.max_tokens:
            payload["options"]["num_predict"] = request.max_tokens

        start_time = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()

            latency_ms = int((time.monotonic() - start_time) * 1000)
            content = data.get("response", "")
            prompt_eval_count = data.get("prompt_eval_count", len(request.prompt.split()))
            eval_count = data.get("eval_count", len(content.split()))

            return LlmResponse(
                content=content,
                input_tokens=prompt_eval_count,
                output_tokens=eval_count,
                latency_ms=latency_ms,
                model_id=self.model_id,
                provider="ollama",
            )

        except Exception as exc:
            if isinstance(exc, OllamaProviderError):
                raise
            raise OllamaProviderError(str(exc)) from exc

    async def extract(self, request: LlmRequest, schema: type[T]) -> Extracted:
        """Extract structured Pydantic model using Ollama JSON format mode."""
        url = f"{self.base_url}/api/generate"
        schema_json = json.dumps(schema.model_json_schema())
        instruction = (
            f"{request.prompt}\n\n"
            f"IMPORTANT: Respond strictly in valid JSON adhering to this schema:\n{schema_json}"
        )

        payload: dict[str, Any] = {
            "model": self.model_id,
            "prompt": instruction,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": request.temperature,
            },
        }
        if request.system_prompt:
            payload["system"] = request.system_prompt
        if request.max_tokens:
            payload["options"]["num_predict"] = request.max_tokens

        start_time = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()

            latency_ms = int((time.monotonic() - start_time) * 1000)
            raw_text = data.get("response", "")
            prompt_eval_count = data.get("prompt_eval_count", len(request.prompt.split()))
            eval_count = data.get("eval_count", len(raw_text.split()))

            parsed_dict = json.loads(raw_text)
            validated_obj = schema.model_validate(parsed_dict)

            return Extracted(
                data=validated_obj,
                input_tokens=prompt_eval_count,
                output_tokens=eval_count,
                latency_ms=latency_ms,
                raw_response=raw_text,
                model_id=self.model_id,
                provider="ollama",
            )

        except Exception as exc:
            if isinstance(exc, OllamaProviderError):
                raise
            raise OllamaProviderError(f"Extraction failed: {exc}") from exc


class OllamaEmbedder(Embedder):
    """Tier 1 local text embedder querying Ollama HTTP daemon."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model_id: str = "nomic-embed-text",
        timeout_seconds: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_id = model_id
        self.timeout_seconds = timeout_seconds

    @property
    def dimension(self) -> int:
        return 768

    async def embed(self, text: str) -> list[float]:
        url = f"{self.base_url}/api/embeddings"
        payload = {"model": self.model_id, "prompt": text}

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                embedding: list[float] = resp.json()["embedding"]
                return embedding
        except Exception as exc:
            raise OllamaProviderError(f"Embedding failed: {exc}") from exc

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        # Ollama's newer /api/embed supports batching, but if it's an older version,
        # we might need to fallback. Assuming newer version for simplicity.
        url = f"{self.base_url}/api/embed"
        payload = {"model": self.model_id, "input": texts}

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    embeddings: list[list[float]] = resp.json()["embeddings"]
                    return embeddings

                # Fallback to sequential
                import asyncio

                tasks = [self.embed(t) for t in texts]
                return await asyncio.gather(*tasks)
        except Exception as exc:
            raise OllamaProviderError(f"Batch embedding failed: {exc}") from exc
