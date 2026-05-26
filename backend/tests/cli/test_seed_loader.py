"""Tests for load_seed_catalogue + filter_seeds_by_providers."""
from pathlib import Path

import pytest

from src.cli.bootstrap import filter_seeds_by_providers, load_seed_catalogue


def _write_yaml(tmp_path: Path, body: str) -> Path:
    f = tmp_path / "models.yaml"
    f.write_text(body)
    return f


def test_load_seed_catalogue_basic(tmp_path: Path) -> None:
    f = _write_yaml(
        tmp_path,
        """
models:
  - display_name: "A"
    model_id: "anthropic:a"
    provider: "anthropic"
    is_default: true
  - display_name: "B"
    model_id: "openai:b"
    provider: "openai"
""",
    )
    catalogue = load_seed_catalogue(f)
    expected_count = 2
    assert len(catalogue) == expected_count
    assert catalogue[0]["model_id"] == "anthropic:a"
    assert catalogue[0]["is_default"] is True


def test_load_seed_catalogue_rejects_multiple_defaults(tmp_path: Path) -> None:
    f = _write_yaml(
        tmp_path,
        """
models:
  - model_id: a
    provider: anthropic
    display_name: A
    is_default: true
  - model_id: b
    provider: openai
    display_name: B
    is_default: true
""",
    )
    with pytest.raises(ValueError, match="at most one"):
        load_seed_catalogue(f)


def test_load_seed_catalogue_missing_models_key(tmp_path: Path) -> None:
    f = _write_yaml(tmp_path, "other: data\n")
    assert load_seed_catalogue(f) == []


def test_filter_seeds_keeps_matching_providers() -> None:
    seeds = [
        {"model_id": "a", "provider": "anthropic", "display_name": "A",
         "is_default": True},
        {"model_id": "b", "provider": "openai", "display_name": "B"},
        {"model_id": "c", "provider": "ollama", "display_name": "C"},
    ]
    filtered = filter_seeds_by_providers(seeds, {"anthropic", "ollama"})
    assert [m["model_id"] for m in filtered] == ["a", "c"]


def test_filter_seeds_promotes_default_when_original_dropped() -> None:
    seeds = [
        {"model_id": "a", "provider": "anthropic", "display_name": "A",
         "is_default": True},
        {"model_id": "b", "provider": "openai", "display_name": "B"},
    ]
    filtered = filter_seeds_by_providers(seeds, {"openai"})
    assert len(filtered) == 1
    assert filtered[0]["model_id"] == "b"
    assert filtered[0]["is_default"] is True


def test_filter_seeds_keeps_existing_default_when_present() -> None:
    seeds = [
        {"model_id": "a", "provider": "anthropic", "display_name": "A",
         "is_default": True},
        {"model_id": "b", "provider": "openai", "display_name": "B"},
    ]
    filtered = filter_seeds_by_providers(seeds, {"anthropic", "openai"})
    assert [m["model_id"] for m in filtered] == ["a", "b"]
    assert filtered[0]["is_default"] is True
    assert filtered[1].get("is_default") in (False, None)


def test_filter_seeds_empty_when_no_match() -> None:
    seeds = [{"model_id": "a", "provider": "anthropic", "display_name": "A"}]
    assert filter_seeds_by_providers(seeds, {"openai"}) == []
