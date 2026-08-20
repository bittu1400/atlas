"""Knowledge Object payload definitions with explicit schema versioning.

As specified in ADR-0003: Stable core columns are typed and queryable; evolving exploratory
fields live in a versioned JSONB payload, upcast on read by pure migration functions.
"""

from typing import Any

from pydantic import BaseModel, Field


class KnowledgePayloadV1(BaseModel):
    """Schema version 1 for exploratory Knowledge Object payload."""

    schema_version: int = Field(default=1, description="Payload schema version")
    summary: str = Field(description="Executive summary of knowledge synthesized for this topic")
    angles: list[str] = Field(
        default_factory=list, description="Candidate narrative and storytelling angles"
    )
    keywords: list[str] = Field(
        default_factory=list, description="Extracted thematic and search keywords"
    )
    psychology_notes: list[str] = Field(
        default_factory=list, description="Audience curiosity triggers and emotional beats"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional unconstrained metadata"
    )
