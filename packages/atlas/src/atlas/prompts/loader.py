"""Versioned prompt template loader and formatter.

Invariants & standards:
- Prompts are never inline string literals in code.
- Every prompt template is stored under packages/atlas/src/atlas/prompts/.
- Template versioning and SHA-256 hash tracking are automatic.
"""

import hashlib
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from atlas.platform.errors import AtlasError

PROMPTS_DIR = Path(__file__).resolve().parent


class PromptNotFoundError(AtlasError):
    """Raised when a requested prompt template file does not exist."""

    def __init__(self, template_name: str) -> None:
        super().__init__(f"Prompt template '{template_name}' not found in {PROMPTS_DIR}")
        self.template_name = template_name


class PromptRenderError(AtlasError):
    """Raised when required template variables are missing during rendering."""

    def __init__(self, template_name: str, missing_vars: list[str]) -> None:
        super().__init__(
            f"Missing required variables for prompt '{template_name}': {', '.join(missing_vars)}"
        )
        self.template_name = template_name
        self.missing_vars = missing_vars


@lru_cache(maxsize=32)
def get_prompt_template(template_name: str) -> str:
    """Read prompt template from filesystem with caching.

    Args:
        template_name: Name of template (e.g. 'claim_extraction_v1' or 'claim_extraction_v1.txt')
    """
    filename = template_name if template_name.endswith(".txt") else f"{template_name}.txt"
    prompt_path = PROMPTS_DIR / filename
    if not prompt_path.is_file():
        raise PromptNotFoundError(template_name)

    return prompt_path.read_text(encoding="utf-8")


def get_prompt_hash(template_name: str) -> str:
    """Compute SHA-256 hash of the raw prompt template."""
    raw_template = get_prompt_template(template_name)
    return hashlib.sha256(raw_template.encode("utf-8")).hexdigest()


def render_prompt(template_name: str, **kwargs: Any) -> str:
    """Render a versioned prompt template with given variable substitutions.

    Replaces {{ variable_name }} with supplied kwargs.
    """
    template = get_prompt_template(template_name)

    # Find all placeholder variables: {{ var_name }}
    placeholders = set(re.findall(r"{{\s*([a-zA-Z0-9_]+)\s*}}", template))
    missing = [var for var in placeholders if var not in kwargs]

    if missing:
        raise PromptRenderError(template_name, missing)

    rendered = template
    for key, val in kwargs.items():
        pattern = re.compile(rf"{{\s*{re.escape(key)}\s*}}")
        rendered = pattern.sub(str(val), rendered)

    return rendered
