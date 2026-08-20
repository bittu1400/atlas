"""Deterministic and prefixed identifier generators for Atlas domain entities."""

import uuid


def generate_id(prefix: str) -> str:
    """Generate a prefixed unique identifier (e.g. ko_1234567890ab).

    Prefixed IDs make logging, debugging, and cross-referencing unambiguous.
    """
    clean_hex = uuid.uuid4().hex[:16]
    return f"{prefix}_{clean_hex}"


def generate_ko_id() -> str:
    """Generate a stable Knowledge Object ID."""
    return generate_id("ko")


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
