"""Unit tests for versioned prompt templates and loader."""

import pytest
from atlas.prompts.loader import (
    PromptNotFoundError,
    PromptRenderError,
    get_prompt_hash,
    get_prompt_template,
    render_prompt,
)


def test_get_prompt_template_success() -> None:
    template = get_prompt_template("claim_extraction_v1")
    assert "Atlas Knowledge Extraction Agent" in template
    assert "{{ topic_title }}" in template


def test_get_prompt_hash_deterministic() -> None:
    hash1 = get_prompt_hash("claim_extraction_v1")
    hash2 = get_prompt_hash("claim_extraction_v1")
    assert hash1 == hash2
    assert len(hash1) == 64


def test_get_prompt_not_found() -> None:
    with pytest.raises(PromptNotFoundError):
        get_prompt_template("non_existent_prompt_template_xyz")


def test_render_prompt_success() -> None:
    rendered = render_prompt(
        "claim_extraction_v1",
        topic_title="Origin of Chess",
        source_title="Ancient History Archive",
        source_url="https://archive.org/details/chess",
        source_tier="primary",
        source_text="Chaturanga was played in 6th century India.",
    )
    assert "Origin of Chess" in rendered
    assert "Ancient History Archive" in rendered
    assert "Chaturanga was played in 6th century India." in rendered
    assert "{{" not in rendered


def test_render_prompt_missing_variables_raises() -> None:
    with pytest.raises(PromptRenderError):
        render_prompt(
            "claim_extraction_v1",
            topic_title="Origin of Chess",
            # Missing source_title, source_url, source_tier, source_text
        )
