from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class License(BaseModel):
    """License definition and permissions."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="License identifier (e.g. CC-BY-4.0)")
    name: str = Field(description="Human readable name")
    permitted_uses: list[str] = Field(default_factory=list)
    restrictions: list[str] = Field(default_factory=list)


class Asset(BaseModel):
    """Media asset with licensing information."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Unique asset identifier")
    url: HttpUrl = Field(description="Location of the asset")
    mime_type: str = Field(description="MIME type")
    license: License = Field(description="Associated license")
    ai_generated: bool = Field(default=False, description="Flag indicating if AI generated")
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(description="Creation timestamp in UTC")


class AssetApproval(BaseModel):
    """Explicit human approval for AI generated assets."""

    model_config = ConfigDict(frozen=True)

    asset_id: str = Field(description="Asset ID being approved")
    gate_id: str = Field(description="Gate ID for this approval")
    actor_id: str = Field(description="Human actor who approved")
    approved_at: datetime = Field(description="Approval timestamp in UTC")
