"""Deterministic and prefixed identifier generators for Atlas domain entities."""

import uuid


def generate_id(prefix: str) -> str:
    """Generate a prefixed unique identifier (e.g. ko_1234567890ab).

    Prefixed IDs make logging, debugging, and cross-referencing unambiguous.
    """
    clean_hex = uuid.uuid4().hex
    return f"{prefix}_{clean_hex}"


def knowledge_object_id_for_topic(topic_id: str) -> str:
    """Return the Knowledge Object ID for a Topic.

    A Topic has exactly one Knowledge Object, so the ID is derived rather than
    minted: the pipeline reconstructs it at stage 8 without carrying it through
    six intervening stages. Both call sites used to spell `f"ko_{topic_id}"`
    inline, which is one rename away from the class of bug that defect B4 was.
    """
    return f"ko_{topic_id}"


def generate_claim_id() -> str:
    """Generate a Claim ID."""
    return generate_id("clm")


def generate_evidence_id() -> str:
    """Generate an Evidence ID."""
    return generate_id("ev")


def generate_source_id() -> str:
    """Generate a Source ID."""
    return generate_id("src")


def generate_snapshot_id() -> str:
    """Generate a Snapshot ID."""
    return generate_id("snp")


def generate_run_id() -> str:
    """Generate a Run ID."""
    return generate_id("run")


def generate_step_id() -> str:
    """Generate a Step ID."""
    return generate_id("stp")


def generate_gate_id() -> str:
    """Generate a Gate ID."""
    return generate_id("gt")


def generate_approval_id() -> str:
    """Generate an Approval ID."""
    return generate_id("appr")


def generate_topic_id() -> str:
    """Generate a Topic ID."""
    return generate_id("top")


def generate_focus_id() -> str:
    """Generate a Focus ID."""
    return generate_id("foc")


def generate_domain_id() -> str:
    """Generate a Domain ID."""
    return generate_id("dom")


def generate_trace_id() -> str:
    """Generate a distributed Trace ID."""
    return f"trc_{uuid.uuid4().hex}"
