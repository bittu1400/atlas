"""Google AI Studio (Gemini) LLM Adapter implementing Llm and StructuredLlm ports.

As specified in ADR-0004 & Invariant 5:
- All provider SDK / API calls are isolated strictly within this adapter.
- Handles structured JSON parsing, token accounting, and capability negotiation.
"""

import json
import time
from typing import Any, TypeVar

import httpx
from atlas.application.ports.llm import (
    Extracted,
    Llm,
    LlmCapabilities,
    LlmRequest,
    LlmResponse,
    StructuredLlm,
)
from atlas.platform.errors import AtlasError
from atlas.platform.redaction import redact_secret
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class GeminiProviderError(AtlasError):
    """Raised when Google AI Studio API returns an error or invalid payload."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Gemini provider error: {message}")


class GeminiLlm(Llm, StructuredLlm):
    """Tier 2 hosted LLM adapter connecting to Google AI Studio REST API."""

    def __init__(
        self,
        api_key: str,
        model_id: str = "gemini-2.0-flash",
        timeout_seconds: float = 30.0,
    ) -> None:
        self.api_key = api_key
        self.model_id = model_id
        self.timeout_seconds = timeout_seconds
        self._capabilities = LlmCapabilities(
            tier=2,
            supports_json=True,
            supports_vision=True,
            context_window_tokens=1_000_000,
            rpm_limit=15,
            rpd_limit=1500,
        )

    @property
    def capabilities(self) -> LlmCapabilities:
        return self._capabilities

    def _redact_error(self, exc: Exception) -> str:
        """Redact API key from exception message (rule R12)."""
        return redact_secret(exc, self.api_key)

    async def complete(self, request: LlmRequest) -> LlmResponse:
        """Generate text completion from prompt using Gemini API."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_id}:generateContent"
        headers = {"x-goog-api-key": self.api_key}
        payload: dict[str, Any] = {
            "contents": [{"parts": [{"text": request.prompt}]}],
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens or 2048,
            },
        }
        if request.system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": request.system_prompt}]}

        start_time = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()

            latency_ms = int((time.monotonic() - start_time) * 1000)

            candidates = data.get("candidates", [])
            if not candidates:
                raise GeminiProviderError("No response candidates returned")

            content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            usage = data.get("usageMetadata", {})
            input_tokens = usage.get("promptTokenCount", len(request.prompt.split()))
            output_tokens = usage.get("candidatesTokenCount", len(content.split()))

            return LlmResponse(
                content=content,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                model_id=self.model_id,
                provider="gemini",
            )

        except Exception as exc:
            if isinstance(exc, GeminiProviderError):
                raise
            raise GeminiProviderError(self._redact_error(exc)) from exc

    async def extract(self, request: LlmRequest, schema: type[T]) -> Extracted:
        """Extract structured Pydantic schema using Gemini JSON response mode."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_id}:generateContent"
        headers = {"x-goog-api-key": self.api_key}

        schema_json = json.dumps(schema.model_json_schema())
        instruction = (
            f"{request.prompt}\n\n"
            f"IMPORTANT: Respond in valid JSON adhering strictly to this JSON Schema:\n{schema_json}"
        )

        payload: dict[str, Any] = {
            "contents": [{"parts": [{"text": instruction}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens or 4096,
            },
        }
        if request.system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": request.system_prompt}]}

        start_time = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()

            latency_ms = int((time.monotonic() - start_time) * 1000)

            candidates = data.get("candidates", [])
            if not candidates:
                raise GeminiProviderError("No response candidates returned for extraction")

            raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            usage = data.get("usageMetadata", {})
            input_tokens = usage.get("promptTokenCount", len(request.prompt.split()))
            output_tokens = usage.get("candidatesTokenCount", len(raw_text.split()))

            # Parse JSON and validate against schema
            parsed_dict = json.loads(raw_text)
            validated_obj = schema.model_validate(parsed_dict)

            return Extracted(
                data=validated_obj,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                raw_response=raw_text,
                model_id=self.model_id,
                provider="gemini",
            )

        except Exception as exc:
            if isinstance(exc, GeminiProviderError):
                raise
            raise GeminiProviderError(f"Extraction failed: {self._redact_error(exc)}") from exc
