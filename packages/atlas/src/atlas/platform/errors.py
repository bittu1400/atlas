"""Typed domain and persistence exceptions for Atlas.

Atlas forbids returning bare Exception or returning None to indicate failure.
Every error has a clear semantic type and diagnostic message.
"""


class AtlasError(Exception):
    """Base exception for all Atlas errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class KnowledgeError(AtlasError):
    """Base error for knowledge management and traceability operations."""


class KnowledgeObjectNotFoundError(KnowledgeError):
    """Raised when a requested Knowledge Object does not exist."""

    def __init__(self, ko_id: str, version: int | None = None) -> None:
        if version is not None:
            super().__init__(f"Knowledge Object '{ko_id}' version {version} not found")
        else:
            super().__init__(f"Knowledge Object '{ko_id}' not found")
        self.ko_id = ko_id
        self.version = version


class TraceabilityConstraintError(KnowledgeError):
    """Raised when an assertion or publication path violates the traceability invariant.

    Invariant 1: Every statement published must trace Claim -> Evidence -> Source -> Snapshot.
    """


class UnsupportedClaimError(KnowledgeError):
    """Raised when an unsupported claim without evidence is placed on a publication path."""


class ClaimNotFoundError(KnowledgeError):
    """Raised when a referenced Claim does not exist."""

    def __init__(self, claim_id: str) -> None:
        super().__init__(f"Claim '{claim_id}' not found")
        self.claim_id = claim_id


class EvidenceNotFoundError(KnowledgeError):
    """Raised when a referenced Evidence does not exist."""

    def __init__(self, evidence_id: str) -> None:
        super().__init__(f"Evidence '{evidence_id}' not found")
        self.evidence_id = evidence_id


class SourceNotFoundError(KnowledgeError):
    """Raised when a referenced Source does not exist."""

    def __init__(self, source_id: str) -> None:
        super().__init__(f"Source '{source_id}' not found")
        self.source_id = source_id


class SnapshotNotFoundError(KnowledgeError):
    """Raised when a referenced Snapshot does not exist."""

    def __init__(self, snapshot_id: str) -> None:
        super().__init__(f"Snapshot '{snapshot_id}' not found")
        self.snapshot_id = snapshot_id


class TopicNotFoundError(KnowledgeError):
    """Raised when a referenced Topic does not exist.

    Defect V-16: without this type, an unknown `topic_id` reached the database
    and came back as SQLAlchemy's `IntegrityError`, which the API answers with
    a 500 because no handler recognises an infrastructure exception.
    """

    def __init__(self, topic_id: str) -> None:
        super().__init__(f"Topic '{topic_id}' not found")
        self.topic_id = topic_id


class FocusError(AtlasError):
    """Base error for Focus and scoping operations."""


class FocusNotFoundError(FocusError):
    """Raised when a referenced Focus does not exist."""

    def __init__(self, focus_id: str) -> None:
        super().__init__(f"Focus '{focus_id}' not found")
        self.focus_id = focus_id


class DomainNotFoundError(FocusError):
    """Raised when a referenced Domain does not exist."""

    def __init__(self, domain_id: str) -> None:
        super().__init__(f"Domain '{domain_id}' not found")
        self.domain_id = domain_id


class ExecutionError(AtlasError):
    """Base error for workflow and pipeline execution."""


class ExtractionTypeError(ExecutionError):
    """Raised when an LLM extraction returns the wrong type."""

    def __init__(self, expected: str, actual: str) -> None:
        super().__init__(f"Expected extraction of type '{expected}', got '{actual}'")
        self.expected = expected
        self.actual = actual


class RunNotFoundError(ExecutionError):
    """Raised when a requested Run is not found."""

    def __init__(self, run_id: str) -> None:
        super().__init__(f"Run '{run_id}' not found")
        self.run_id = run_id


class StepNotFoundError(ExecutionError):
    """Raised when a requested Step is not found."""

    def __init__(self, step_id: str) -> None:
        super().__init__(f"Step '{step_id}' not found")
        self.step_id = step_id


class GateNotFoundError(ExecutionError):
    """Raised when a requested Gate is not found."""

    def __init__(self, gate_id: str) -> None:
        super().__init__(f"Gate '{gate_id}' not found")
        self.gate_id = gate_id


class GateAlreadyResolvedError(ExecutionError):
    """Raised when attempting to approve or reject an already resolved Gate."""

    def __init__(self, gate_id: str, status: str) -> None:
        super().__init__(f"Gate '{gate_id}' is already resolved with status '{status}'")
        self.gate_id = gate_id
        self.status = status


class InvalidGateDecisionError(ExecutionError):
    """Raised when an invalid approval decision or malformed rejection feedback is supplied."""


class InvalidStateTransitionError(ExecutionError):
    """Raised when attempting an illegal state machine transition."""

    def __init__(self, current_state: str, target_state: str) -> None:
        super().__init__(f"Cannot transition from state '{current_state}' to '{target_state}'")
        self.current_state = current_state
        self.target_state = target_state


class ProductionArtifactNotFoundError(ExecutionError):
    """Raised when a stage needs a persisted production artifact that is missing.

    Stages 10-18 read the Script, TimingPlan, Storyboard and RenderArtifact the
    earlier stages wrote. A missing row means the pipeline would have to invent
    one, which is exactly what Invariant 7 forbids.
    """

    def __init__(self, artifact_kind: str, artifact_id: str) -> None:
        super().__init__(f"{artifact_kind} '{artifact_id}' not found")
        self.artifact_kind = artifact_kind
        self.artifact_id = artifact_id


class UnapprovedScriptError(ExecutionError):
    """Raised when a render is attempted from a script whose claims are not all verified."""

    def __init__(self, script_id: str, offending_claim_ids: list[str]) -> None:
        super().__init__(
            f"Script '{script_id}' references claims that are not verified with evidence: "
            f"{', '.join(sorted(offending_claim_ids))}"
        )
        self.script_id = script_id
        self.offending_claim_ids = offending_claim_ids


class PublisherNotConfiguredError(ExecutionError):
    """Raised when the publish stage runs without a Publisher wired into the runner."""

    def __init__(self, run_id: str) -> None:
        super().__init__(f"Run '{run_id}' reached the publish stage with no publisher configured")
        self.run_id = run_id


class StepExecutionError(ExecutionError):
    """Raised when a pipeline step fails during execution."""

    def __init__(self, step_name: str, reason: str) -> None:
        super().__init__(f"Step '{step_name}' failed: {reason}")
        self.step_name = step_name
        self.reason = reason


class QualityGateFailedError(ExecutionError):
    """Raised when a render artifact fails the quality rubric hard gate."""

    def __init__(self, weighted_score: float, reason: str) -> None:
        super().__init__(f"Quality gate failed with score {weighted_score:.1f}: {reason}")
        self.weighted_score = weighted_score
        self.reason = reason


class ResourceLockHeldError(ExecutionError):
    """Raised when acquiring a resource lock (e.g. GPU lease) that is currently held."""

    def __init__(self, resource_name: str, holder_id: str) -> None:
        super().__init__(f"Resource lock for '{resource_name}' is currently held by '{holder_id}'")
        self.resource_name = resource_name
        self.holder_id = holder_id


class QuotaExceededError(ExecutionError):
    """Raised when an operation exceeds daily or per-minute provider quota budget."""

    def __init__(self, provider: str, limit_type: str) -> None:
        super().__init__(f"Quota exceeded for provider '{provider}' ({limit_type} limit)")
        self.provider = provider
        self.limit_type = limit_type


class RateLimitExceededError(ExecutionError):
    """Raised when a provider's requests-per-minute threshold is hit."""

    def __init__(self, provider: str, limit_type: str = "RPM") -> None:
        super().__init__(f"Rate limit exceeded for provider '{provider}' ({limit_type})")
        self.provider = provider
        self.limit_type = limit_type


class PolicyError(AtlasError):
    """Base error for policy enforcement (license, gate, quality)."""


class LicenseIncompatibleError(PolicyError):
    """Raised when an asset's license forbids the intended use (Invariant 10)."""

    def __init__(self, asset_id: str, license_id: str, reason: str) -> None:
        super().__init__(f"Asset '{asset_id}' license '{license_id}' is incompatible: {reason}")
        self.asset_id = asset_id
        self.license_id = license_id
        self.reason = reason


class AiImageUnapprovedError(PolicyError):
    """Raised when AI-generated imagery lacks explicit human approval (Invariant 9)."""

    def __init__(self, asset_id: str) -> None:
        super().__init__(
            f"AI-generated asset '{asset_id}' requires explicit human approval before render"
        )
        self.asset_id = asset_id


class PublishingError(AtlasError):
    """Base error for publishing identities and their configuration."""


class ChannelNotFoundError(PublishingError):
    """Raised when a referenced Channel does not exist."""

    def __init__(self, channel_id: str) -> None:
        super().__init__(f"Channel '{channel_id}' not found")
        self.channel_id = channel_id


class SchedulingError(AtlasError):
    """Base error for publishing schedule and timezone resolution."""


class BlackoutWindowViolationError(SchedulingError):
    """Raised when a proposed publish slot violates the 22:00-06:00 audience-local blackout rule."""

    def __init__(self, slot_local_time: str) -> None:
        super().__init__(
            f"Publish slot at '{slot_local_time}' violates the 22:00-06:00 audience-local blackout rule"
        )
        self.slot_local_time = slot_local_time
