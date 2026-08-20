"""Pure upcasting functions for migrating legacy JSONB payloads to the latest schema version.

As required by ADR-0003: Payload upcasting must be pure, tested, and never lossy.
"""

from typing import Any

from atlas.domain.knowledge.payload import KnowledgePayloadV1


def upcast_knowledge_payload(raw_payload: dict[str, Any] | None) -> KnowledgePayloadV1:
    """Upcast a raw dictionary from the database to the current KnowledgePayload version.

    Handles legacy payloads without schema_version (assumed v0) by migrating up to v1.
    """
    if raw_payload is None:
        return KnowledgePayloadV1(
            summary="", angles=[], keywords=[], psychology_notes=[], metadata={}
        )

    version = raw_payload.get("schema_version", 0)

    payload = dict(raw_payload)

    # Migrate v0 (unversioned legacy payload) -> v1
    if version == 0:
        summary = payload.get("summary") or payload.get("overview") or ""
        angles = payload.get("angles") or payload.get("story_angles") or []
        keywords = payload.get("keywords") or []
        psychology_notes = payload.get("psychology_notes") or []
        metadata = {
            k: v
            for k, v in payload.items()
            if k
            not in {"summary", "overview", "angles", "story_angles", "keywords", "psychology_notes"}
        }
        return KnowledgePayloadV1(
            schema_version=1,
            summary=str(summary),
            angles=list(angles),
            keywords=list(keywords),
            psychology_notes=list(psychology_notes),
            metadata=metadata,
        )

    if version == 1:
        return KnowledgePayloadV1.model_validate(payload)

    # Future versions can chain here (e.g. v1 -> v2 -> v3)
    return KnowledgePayloadV1.model_validate(payload)
