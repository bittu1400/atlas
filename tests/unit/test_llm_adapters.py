"""Unit tests for Gemini and Ollama LLM Adapters with mocked HTTP transport."""

import json
from typing import Any

import pytest
from atlas.adapters.llm.gemini import GeminiLlm
from atlas.adapters.llm.ollama import OllamaLlm
from atlas.application.ports.llm import LlmRequest
from pydantic import BaseModel


class MockExtractionSchema(BaseModel):
    summary: str
    confidence: float


@pytest.mark.asyncio
async def test_gemini_llm_capabilities() -> None:
    gemini = GeminiLlm(api_key="test_key")
    caps = gemini.capabilities
    assert caps.tier == 2
    assert caps.supports_json is True
    assert caps.rpm_limit == 15
    assert caps.rpd_limit == 1500


@pytest.mark.asyncio
async def test_ollama_llm_capabilities() -> None:
    ollama = OllamaLlm()
    caps = ollama.capabilities
    assert caps.tier == 1
    assert caps.supports_json is True
    assert caps.context_window_tokens == 32768


@pytest.mark.asyncio
async def test_gemini_llm_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    gemini = GeminiLlm(api_key="fake_key")

    mock_resp_payload: dict[str, Any] = {
        "candidates": [{"content": {"parts": [{"text": "Gemini generated text completion."}]}}],
        "usageMetadata": {
            "promptTokenCount": 12,
            "candidatesTokenCount": 5,
        },
    }

    class MockResponse:
        status_code = 200

        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict[str, Any]:
            return mock_resp_payload

    class MockAsyncClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        async def __aenter__(self) -> "MockAsyncClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            pass

        async def post(
            self, _url: str, json: dict[str, Any] | None = None, **_kwargs: object
        ) -> MockResponse:
            _ = json
            return MockResponse()

    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    req = LlmRequest(prompt="Tell me about chess origins.")
    res = await gemini.complete(req)

    assert res.content == "Gemini generated text completion."
    assert res.input_tokens == 12
    assert res.output_tokens == 5
    assert res.provider == "gemini"


@pytest.mark.asyncio
async def test_gemini_llm_extract(monkeypatch: pytest.MonkeyPatch) -> None:
    gemini = GeminiLlm(api_key="fake_key")

    mock_resp_payload: dict[str, Any] = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": json.dumps({"summary": "Chess history.", "confidence": 0.99})}
                    ]
                }
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 25,
            "candidatesTokenCount": 10,
        },
    }

    class MockResponse:
        status_code = 200

        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict[str, Any]:
            return mock_resp_payload

    class MockAsyncClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        async def __aenter__(self) -> "MockAsyncClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            pass

        async def post(
            self, _url: str, json: dict[str, Any] | None = None, **_kwargs: object
        ) -> MockResponse:
            _ = json
            return MockResponse()

    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    req = LlmRequest(prompt="Extract summary from text.")
    extracted = await gemini.extract(req, MockExtractionSchema)

    assert isinstance(extracted.data, MockExtractionSchema)
    assert extracted.data.summary == "Chess history."
    assert extracted.data.confidence == 0.99


@pytest.mark.asyncio
async def test_ollama_llm_complete_and_extract(monkeypatch: pytest.MonkeyPatch) -> None:
    ollama = OllamaLlm()

    mock_resp_payload: dict[str, Any] = {
        "response": json.dumps({"summary": "Ollama summary.", "confidence": 0.95}),
        "prompt_eval_count": 20,
        "eval_count": 15,
    }

    class MockResponse:
        status_code = 200

        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict[str, Any]:
            return mock_resp_payload

    class MockAsyncClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        async def __aenter__(self) -> "MockAsyncClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            pass

        async def post(
            self, _url: str, json: dict[str, Any] | None = None, **_kwargs: object
        ) -> MockResponse:
            _ = json
            return MockResponse()

    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    req = LlmRequest(prompt="Extract summary with Ollama.")
    extracted = await ollama.extract(req, MockExtractionSchema)

    assert isinstance(extracted.data, MockExtractionSchema)
    assert extracted.data.summary == "Ollama summary."
    assert extracted.data.confidence == 0.95
