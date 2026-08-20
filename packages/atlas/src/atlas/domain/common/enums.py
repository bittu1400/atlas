"""Shared enumerations used across multiple domain modules."""

from enum import StrEnum


class SourceTier(StrEnum):
    """Classification of source reliability and provenance."""

    PRIMARY = "primary"
    PEER_REVIEWED = "peer_reviewed"
    INSTITUTIONAL = "institutional"
    REFERENCE = "reference"
    UNVETTED = "unvetted"
