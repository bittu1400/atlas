"""Port interfaces for Language Models and Structured Extraction.

As specified in ARCHITECTURE.md §5 and ADR-0004:
- Language models never supply facts; they extract, structure, rank, phrase, and judge.
- Capability negotiation allows routers to inspect context window and JSON support.
"""

from typing import Any, Protocol, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T", bound=BaseModel)


class LlmCapabilities(BaseModel):
    """Capabilities exposed by a language model provider."""

    model_config = ConfigDict(frozen=True)

    tier: int = Field(description="Tier ladder level (1=local Ollama, 2=hosted frontier)")
    supports_json: bool = Field(default=True, description="Native JSON output support")
    supports_vision: bool = Field(default=False, description="Vision / multimodal input support")
    context_window_tokens: int = Field(default=8192, description="Maximum context window size")
    rpm_limit: int = Field(default=15, description="Requests per minute limit")
    rpd_limit: int = Field(default=1500, description="Requests per day limit")


class LlmRequest(BaseModel):
    """Normalized request passed to an LLM provider."""

    model_config = ConfigDict(frozen=True)

    prompt: str = Field(description="Formatted user prompt")
    system_prompt: str | None = Field(default=None, description="System instruction")
    prompt_version: str = Field(
        default="v1", description="Identifier of the versioned prompt template"
    )
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int | None = Field(default=2048, description="Maximum tokens to generate")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Additional model parameters"
    )


class LlmResponse(BaseModel):
    """Normalized response returned by an LLM provider."""

    model_config = ConfigDict(frozen=True)

    content: str = Field(description="Generated text response")
    input_tokens: int = Field(ge=0, description="Number of input tokens consumed")
    output_tokens: int = Field(ge=0, description="Number of output tokens generated")
    latency_ms: int = Field(ge=0, description="Roundtrip latency in milliseconds")
    model_id: str = Field(description="Model identifier that executed the call")
    provider: str = Field(description="Provider name (gemini, ollama, fake)")


class Extracted(BaseModel):
    """Validated structured output extracted by a model."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    data: Any = Field(description="Parsed and validated Pydantic model instance")
    input_tokens: int = Field(ge=0, description="Input tokens used")
    output_tokens: int = Field(ge=0, description="Output tokens used")
    latency_ms: int = Field(ge=0, description="Latency in ms")
    raw_response: str = Field(description="Raw text output before parsing")


class Llm(Protocol):
    """Port for raw text generation models."""

    @property
    def capabilities(self) -> LlmCapabilities:
        """Inspect provider capabilities."""
        ...

    async def complete(self, request: LlmRequest) -> LlmResponse:
        """Generate text completion from a prompt."""
        ...


class StructuredLlm(Protocol):
    """Port for schema-validated structured information extraction."""

    @property
    def capabilities(self) -> LlmCapabilities:
        """Inspect provider capabilities."""
        ...

    async def extract(self, request: LlmRequest, schema: type[T]) -> Extracted:
        """Extract structured Pydantic model from prompt with schema enforcement."""
        ...
