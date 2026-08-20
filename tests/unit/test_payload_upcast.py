"""Unit tests for Knowledge Payload version upcasting as specified in ADR-0003."""

from atlas.domain.knowledge.payload import KnowledgePayloadV1
from atlas.domain.knowledge.upcast import upcast_knowledge_payload


def test_upcasts_none_payload_to_default_v1() -> None:
    """Upcasting None creates a valid empty V1 payload."""
    payload = upcast_knowledge_payload(None)
    assert payload.schema_version == 1
    assert payload.summary == ""
    assert payload.angles == []
    assert payload.keywords == []


def test_upcasts_v0_legacy_payload_to_v1() -> None:
    """Upcasting legacy unversioned payload preserves all fields and custom metadata."""
    legacy_data = {
        "overview": "Comprehensive tiger biology synthesis",
        "story_angles": ["The Ghost of the Sundarbans", "Apex in Crisis"],
        "keywords": ["tiger", "panthera", "predator"],
        "psychology_notes": ["Awe", "Urgency"],
        "custom_legacy_field": 12345,
    }
    payload = upcast_knowledge_payload(legacy_data)

    assert isinstance(payload, KnowledgePayloadV1)
    assert payload.schema_version == 1
    assert payload.summary == "Comprehensive tiger biology synthesis"
    assert payload.angles == ["The Ghost of the Sundarbans", "Apex in Crisis"]
    assert payload.keywords == ["tiger", "panthera", "predator"]
    assert payload.psychology_notes == ["Awe", "Urgency"]
    assert payload.metadata == {"custom_legacy_field": 12345}


def test_validates_existing_v1_payload() -> None:
    """V1 payload passes through validation cleanly."""
    v1_data = {
        "schema_version": 1,
        "summary": "Modern tiger distribution",
        "angles": ["Genetic isolation"],
        "keywords": ["genetics", "range"],
        "psychology_notes": ["Scientific wonder"],
        "metadata": {"source_count": 5},
    }
    payload = upcast_knowledge_payload(v1_data)
    assert payload.schema_version == 1
    assert payload.summary == "Modern tiger distribution"
    assert payload.metadata["source_count"] == 5
