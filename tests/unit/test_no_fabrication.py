"""Unit tests for anti-fabrication guards and secret redaction (T-08, T-09, T-35, ADR-0014).

These checks enforce:
- Rule R1/R2: No hardcoded payloads or mock returns in real adapters (Guard 1).
- Rule R2/Invariant 5: No fakes imports in production code (Guard 2).
- Rule R2: No StubBroker in queue adapters (Guard 3).
- Rule R3: No real provider class returning hardcoded literals (Guard 4).
- Rule R12: Secrets never leak into URLs or exceptions (Guard 5, T-09).
- Rule R10: Policy validation methods have real production callers (Guard 6).
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


@pytest.mark.xfail(
    strict=True,
    reason="Defects C-01, C-02: Production container imports fakes (remediated in T-26)",
)
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


@pytest.mark.xfail(
    strict=True,
    reason="Defects C-04, C-05, C-06: Stubs wear real provider names and return literals (remediated in T-27/T-28)",
)
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


@pytest.mark.xfail(
    strict=True,
    reason="Defect D-05: validate_ai_image_approval has no production callers (remediated in T-16)",
)
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


@pytest.mark.xfail(
    strict=True,
    reason="Defect F-04: STATUS.md contains unmeasured bare metric claims (remediated in T-31)",
)
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
