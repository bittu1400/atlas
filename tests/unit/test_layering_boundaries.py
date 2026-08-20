"""Architectural test verifying Clean Architecture import boundaries.

Rule from ARCHITECTURE.md §1 & CLAUDE.md:
`domain/` imports nothing from Atlas outside itself and nothing from any I/O library
(e.g. sqlalchemy, httpx, asyncpg, psycopg, pydantic_settings, etc.).
"""

import ast
from pathlib import Path

FORBIDDEN_MODULES = {
    "sqlalchemy",
    "alembic",
    "asyncpg",
    "psycopg",
    "httpx",
    "pydantic_settings",
    "fastapi",
    "dramatiq",
    "typer",
}


def test_domain_layer_has_no_io_dependencies() -> None:
    """Verify that every python file in atlas.domain does not import forbidden I/O packages."""
    domain_dir = Path("packages/atlas/src/atlas/domain")
    python_files = list(domain_dir.rglob("*.py"))

    assert len(python_files) > 0, "No domain files found to check"

    violations: list[str] = []

    for file_path in python_files:
        tree = ast.parse(file_path.read_text(), filename=str(file_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_pkg = alias.name.split(".")[0]
                    if root_pkg in FORBIDDEN_MODULES:
                        violations.append(f"{file_path}: imports '{alias.name}'")
                    if root_pkg == "atlas" and len(alias.name.split(".")) > 1:
                        sub_pkg = alias.name.split(".")[1]
                        if sub_pkg in {"adapters", "entrypoints", "application"}:
                            violations.append(
                                f"{file_path}: domain illegally imports from '{alias.name}'"
                            )
            elif isinstance(node, ast.ImportFrom) and node.module:
                root_pkg = node.module.split(".")[0]
                if root_pkg in FORBIDDEN_MODULES:
                    violations.append(f"{file_path}: imports from '{node.module}'")
                if root_pkg == "atlas" and len(node.module.split(".")) > 1:
                    sub_pkg = node.module.split(".")[1]
                    if sub_pkg in {"adapters", "entrypoints", "application"}:
                        violations.append(
                            f"{file_path}: domain illegally imports from '{node.module}'"
                        )

    assert not violations, "Layering rule violations found in domain/:\n" + "\n".join(violations)
