"""Unit tests for anti-fabrication guards and secret redaction (T-08, T-09, T-35, ADR-0014).

These checks enforce:
- Rule R1/R2: No hardcoded payloads or mock returns in real adapters (Guard 1).
- Rule R2/Invariant 5: No fakes imports in production code (Guard 2).
- Rule R2: No StubBroker in queue adapters (Guard 3).
- Rule R3: No real provider class returning hardcoded literals (Guard 4).
- Rule R12: Secrets never leak into URLs or exceptions (Guard 5, T-09).
- Rule R10: Policy validation methods have real production callers (Guard 6).
- Rule R4: No sentence shaped like a historical fact inside a fake (Guard 7, SC-01).
- Rule R7: STATUS.md honesty metrics (T-35).
"""

import ast
import re
from pathlib import Path
from typing import Any

import httpx
import pytest
from atlas.adapters.llm.gemini import GeminiLlm, GeminiProviderError
from atlas.application.ports.llm import LlmRequest

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "packages" / "atlas" / "src" / "atlas"
ADAPTERS_DIR = SRC_DIR / "adapters"
FAKES_DIR = ADAPTERS_DIR / "fakes"

# Guard 7 (SC-01, rule R4): the shape of a plausible historical sentence — a century reference,
# a named polity, a dated claim, or the language of attestation.
PLAUSIBLE_HISTORY_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b\d{1,2}(?:st|nd|rd|th)[- ]century\b", re.I), "century reference"),
    (re.compile(r"\b(?:in|by|around|circa|c\.)\s+\d{3,4}\b", re.I), "dated claim"),
    (re.compile(r"\b\d{3,4}\s*(?:BCE?|AD|CE)\b"), "dated claim"),
    (
        re.compile(
            r"\b(?:empire|dynasty|kingdom|caliphate|sultanate|emperor|pharaoh|antiquity)\b", re.I
        ),
        "named polity",
    ),
    (
        re.compile(
            r"\b(?:historical records|attests?|attested|treatises?|manuscripts?|chronicles?|"
            r"archaeolog\w+|excavat\w+)\b",
            re.I,
        ),
        "attestation language",
    ),
)


def test_guard_1_no_dummy_or_mock_in_real_adapters() -> None:
    """Rule R1, R2: No dummy/mock strings or schema.__name__ ladders in real adapters."""
    checked_subdirs = ["llm", "images", "sources", "search", "publish", "renderer", "audio"]
    violations = []

    for subdir in checked_subdirs:
        adapter_path = ADAPTERS_DIR / subdir
        if not adapter_path.exists():
            continue
        for py_file in adapter_path.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(py_file))
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Compare)
                    and isinstance(node.left, ast.Attribute)
                    and node.left.attr == "__name__"
                ):
                    violations.append(f"{py_file.name}: schema.__name__ comparison detected (F-01)")
                if (
                    isinstance(node, ast.Constant)
                    and isinstance(node.value, str)
                    and node.value.lower() in ("dummy", "mock_dummy")
                    and "test" not in py_file.name
                ):
                    violations.append(f"{py_file.name}: literal '{node.value}' detected")

    assert not violations, f"Anti-fabrication violations found: {violations}"


def test_guard_2_no_fakes_imported_in_production_modules() -> None:
    """Rule R2, Invariant 5: No module outside adapters/fakes/ imports atlas.adapters.fakes."""
    violations = []

    for py_file in SRC_DIR.rglob("*.py"):
        if "adapters/fakes" in str(py_file):
            continue
        rel_path = str(py_file.relative_to(SRC_DIR))
        content = py_file.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if "atlas.adapters.fakes" in alias.name:
                        violations.append(f"{rel_path}: imports {alias.name}")
            elif (
                isinstance(node, ast.ImportFrom)
                and node.module
                and "atlas.adapters.fakes" in node.module
            ):
                violations.append(f"{rel_path}: imports from {node.module}")

    assert not violations, f"Fakes imports detected in production code: {violations}"


def test_guard_3_queue_adapter_does_not_reference_stub_broker() -> None:
    """Rule R2: No adapters/queue/*.py references StubBroker."""
    queue_dir = ADAPTERS_DIR / "queue"
    violations = []
    if queue_dir.exists():
        for py_file in queue_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            if "StubBroker" in content:
                violations.append(str(py_file.relative_to(SRC_DIR)))
    assert not violations, f"StubBroker referenced in queue adapter: {violations}"


def test_guard_4_real_provider_classes_do_not_return_literals() -> None:
    """Rule R3: Classes named after real providers must not return hardcoded literals from port methods."""
    provider_class_prefixes = (
        "Gemini",
        "Ollama",
        "YouTube",
        "Freesound",
        "Wikimedia",
        "Remotion",
        "StableDiffusion",
        "LocalStableDiffusion",
        "Thumbnail",
    )
    violations = []

    for py_file in ADAPTERS_DIR.rglob("*.py"):
        if "fakes" in str(py_file):
            continue
        content = py_file.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and any(
                p in node.name for p in provider_class_prefixes
            ):
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        for subnode in ast.walk(item):
                            if (
                                isinstance(subnode, ast.Return)
                                and subnode.value is not None
                                and isinstance(subnode.value, ast.Constant)
                                and isinstance(subnode.value.value, (str, bytes))
                            ):
                                val = str(subnode.value.value)
                                if "mock" in val or "STABLE_DIFFUSION" in val:
                                    violations.append(
                                        f"{py_file.name}::{node.name}.{item.name} returns literal '{val}'"
                                    )

    assert not violations, f"Rule R3 violations found (stubs with provider names): {violations}"


def test_guard_5_no_api_keys_in_url_constructions() -> None:
    """Rule R12: No ?key= or key={ in URL constructions under adapters/."""
    violations = []
    for py_file in ADAPTERS_DIR.rglob("*.py"):
        if "fakes" in str(py_file):
            continue
        content = py_file.read_text(encoding="utf-8")
        if "?key=" in content or "key={" in content:
            violations.append(str(py_file.relative_to(SRC_DIR)))
    assert not violations, f"API keys detected in URL construction: {violations}"


def test_guard_6_policy_validation_methods_have_production_callers() -> None:
    """Rule R10: Policy validation methods must have callers outside tests/ (catches D-05)."""
    policies_dir = SRC_DIR / "application" / "policies"
    policy_methods: list[str] = []

    for py_file in policies_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
                node.name.startswith("validate_") or node.name.startswith("enforce_")
            ):
                policy_methods.append(node.name)

    uncalled: list[str] = []
    for method in policy_methods:
        call_found = False
        for search_dir in [SRC_DIR / "application", SRC_DIR / "adapters", REPO_ROOT / "apps"]:
            for py_file in search_dir.rglob("*.py"):
                if py_file.parent == policies_dir:
                    continue
                content = py_file.read_text(encoding="utf-8")
                if method in content:
                    call_found = True
                    break
            if call_found:
                break
        if not call_found:
            uncalled.append(method)

    assert not uncalled, (
        f"Policy validation methods have no production callers (decorative invariants): {uncalled}"
    )


def _plausible_history_hits(text: str) -> list[str]:
    """Return the names of every plausible-history pattern the text matches.

    Guard 7 exists because none of Guards 1-6 caught SC-01: two fabricated historical sentences
    typed into a fake so a verbatim-evidence check would find something to match. The patterns are
    crude on purpose — a false positive costs a rename, a false negative cost the 2026-08-29
    incident.
    """
    return [name for pattern, name in PLAUSIBLE_HISTORY_PATTERNS if pattern.search(text)]


def test_guard_7_no_plausible_history_in_fakes() -> None:
    """Rule R4, SC-01: A fake may carry synthetic shape, never a sentence shaped like a fact."""
    violations: list[str] = []

    for py_file in FAKES_DIR.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            hits = _plausible_history_hits(node.value)
            if hits:
                violations.append(f"{py_file.name}:{node.lineno}: {hits} in {node.value[:80]!r}")

    assert not violations, (
        "Fakes contain sentences shaped like historical facts (rule R4, defect SC-01). "
        f"A fake must read as obviously synthetic: {violations}"
    )


# Keyword arguments whose value becomes the content of a claim, an evidence quote, or a source
# snippet. A century reference in a `value=` facet or an operator's critique is ordinary text; the
# same words in one of these is a fact the fixture invented.
CLAIM_SHAPED_KWARGS = frozenset({"text", "quote", "summary", "snippet", "narrative_thesis"})


def test_guard_7_no_plausible_history_in_claim_shaped_fixtures() -> None:
    """Rule R4: fixtures may carry synthetic shape, never an invented fact, anywhere in the repo."""
    violations: list[str] = []

    for search_dir in (REPO_ROOT / "tests", SRC_DIR):
        for py_file in search_dir.rglob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if not isinstance(node, ast.keyword) or node.arg not in CLAIM_SHAPED_KWARGS:
                    continue
                value = node.value
                if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
                    continue
                hits = _plausible_history_hits(value.value)
                if hits:
                    rel = py_file.relative_to(REPO_ROOT)
                    violations.append(f"{rel}:{value.lineno}: {hits} in {value.value[:80]!r}")

    assert not violations, (
        "Claim-shaped fixtures contain invented historical facts (rule R4). Fixtures must be "
        f"obviously synthetic: {violations}"
    )


def test_guard_7_detector_catches_a_fabricated_sentence() -> None:
    """The guard is only worth its runtime if it fires; SC-01 slipped past six guards that did not."""
    fabricated = (
        "Historical records attest that PLACEHOLDER_GAME was played in the Wibble Empire "
        "court in the 6th century."
    )
    assert _plausible_history_hits(fabricated)
    assert not _plausible_history_hits("SUBJECT_A was recorded by SOURCE_B.")


def test_status_honesty_check() -> None:
    """T-35, Rule R7: STATUS.md must contain no bare unmeasured metric claims (ADR-0014 §5)."""
    status_file = REPO_ROOT / "docs" / "STATUS.md"
    assert status_file.exists()
    content = status_file.read_text(encoding="utf-8")

    bare_claims = []
    pattern = re.compile(
        r"0 lint violations|0 (strict )?mypy (type )?errors|\d+ (unit, integration, and end-to-end )?tests passing",
        re.IGNORECASE,
    )
    for line in content.splitlines():
        if pattern.search(line) and not re.search(r"\b20\d{2}-\d{2}-\d{2}\b", line):
            bare_claims.append(line.strip())

    assert not bare_claims, (
        f"STATUS.md contains bare metric claims without measurement date: {bare_claims}"
    )


@pytest.mark.asyncio
async def test_secret_redaction_in_gemini_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """T-09, Rule R12: GeminiProviderError raised on failing request redacts API key."""
    secret_key = "AIzaSySecretApiKey123456789"
    adapter = GeminiLlm(api_key=secret_key, model_id="gemini-2.0-flash")

    # Mock httpx to simulate a network connection error containing the secret key
    def mock_handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"Connection to Gemini API failed with key={secret_key}")

    transport = httpx.MockTransport(mock_handler)
    real_async_client = httpx.AsyncClient

    def mock_async_client(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", mock_async_client)

    with pytest.raises(GeminiProviderError) as exc_info:
        await adapter.complete(LlmRequest(prompt="Hello"))

    err_msg = str(exc_info.value)
    assert secret_key not in err_msg, f"Secret key leaked in error message: {err_msg}"
    assert "[REDACTED_API_KEY]" in err_msg, f"Expected redaction marker in: {err_msg}"


@pytest.mark.asyncio
async def test_secret_redaction_in_freesound_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """T-10, Rule R12: FreesoundProviderError raised on failing request redacts API key."""
    from atlas.adapters.audio.freesound import FreesoundLibrary, FreesoundProviderError

    secret_key = "FreesoundApiKeySecret987654321"
    adapter = FreesoundLibrary(api_key=secret_key)

    def mock_handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"Connection to Freesound API failed with token={secret_key}")

    transport = httpx.MockTransport(mock_handler)
    real_async_client = httpx.AsyncClient

    def mock_async_client(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", mock_async_client)

    with pytest.raises(FreesoundProviderError) as exc_info:
        await adapter.get_music_bed("cinematic")

    err_msg = str(exc_info.value)
    assert secret_key not in err_msg, f"Secret key leaked in error message: {err_msg}"
    assert "[REDACTED_API_KEY]" in err_msg, f"Expected redaction marker in: {err_msg}"
